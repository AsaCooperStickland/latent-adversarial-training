from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union
from contextlib import nullcontext

from llmtuner.extras.constants import IGNORE_INDEX
from llmtuner.extras.logging import get_logger

if TYPE_CHECKING:
    from transformers.trainer import PredictionOutput

import torch.nn.functional as F
from transformers.modeling_utils import unwrap_model
from transformers.models.auto.modeling_auto import MODEL_FOR_CAUSAL_LM_MAPPING_NAMES
from peft import PeftModel
from trl.core import logprobs_from_logits

from llmtuner.train.sft.trainer import CustomSeq2SeqTrainer


logger = get_logger(__name__)


class SteeringTrainer(CustomSeq2SeqTrainer):
    def __init__(self, custom_args, steering, **kwargs):
        super().__init__(**kwargs)
        self.custom_args = custom_args
        self.steering = steering
        self.kl_loss = custom_args["loss_function"] == "kl"
        print(self.model)
        print(self.accelerator.unwrap_model(self.model))
        self.optional_peft_ctx = (
            self.model.disable_adapter
            if (isinstance(self.model, PeftModel) and self.kl_loss)
            else nullcontext
        )

    def compute_loss(self, model, inputs, return_outputs=False):
        """
        How the loss is computed by Trainer. By default, all models return the loss in the first element.

        Subclass and override for custom behavior.
        """
        self.steering.do_shift(mode='train')
        
        if self.label_smoother is not None and "labels" in inputs:
            labels = inputs.pop("labels")
        else:
            labels = None
        outputs = model(**inputs)

        self.steering.reset()
        if self.kl_loss:
            logprobs = logprobs_from_logits(outputs.logits, None, gather=False)
            model.eval()
            with self.optional_peft_ctx():
                original_outputs = model(**inputs)
                original_logprobs = logprobs_from_logits(original_outputs.logits, None, gather=False)
            model.train()

        # Save past state if it exists
        # TODO: this needs to be fixed and made cleaner later.
        if self.args.past_index >= 0:
            self._past = outputs[self.args.past_index]
        
        if self.kl_loss:
                loss = F.kl_div(original_logprobs, logprobs, log_target=True, reduction="none").sum(-1)
                print(loss)
                loss = loss.mean(-1).mean(-1)
                print(loss)
        elif labels is not None:
            if unwrap_model(model)._get_name() in MODEL_FOR_CAUSAL_LM_MAPPING_NAMES.values():
                loss = self.label_smoother(outputs, labels, shift_labels=True)
            else:
                loss = self.label_smoother(outputs, labels)
        else:
            if isinstance(outputs, dict) and "loss" not in outputs:
                raise ValueError(
                    "The model did not return a loss from the inputs, only the following keys: "
                    f"{','.join(outputs.keys())}. For reference, the inputs it received are {','.join(inputs.keys())}."
                )
            # We don't use .loss here since the model may return tuples instead of ModelOutput.
            loss = outputs["loss"] if isinstance(outputs, dict) else outputs[0]
        if self.custom_args['optimize_steering']:
            self.steering.log(loss)

        return (loss, outputs) if return_outputs else loss
    
    def save_model(self, output_dir: Optional[str] = None, _internal_call: bool = False):
        """
        Will save the model, so you can reload it using `from_pretrained()`.

        Will only save from the main process.
        """
        
        self.steering.reset()
        self.steering.wrapped_model.unwrap()
        super().save_model(output_dir, _internal_call)
        self.steering.wrapped_model.wrap_block(self.steering.layer_id, block_name=self.steering.block_name)