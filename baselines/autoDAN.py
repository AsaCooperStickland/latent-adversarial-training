import numpy as np
import torch
import torch.nn as nn
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                          GPTNeoXForCausalLM)
from tqdm import tqdm

SOFTMAX_FINAL = nn.Softmax(dim=-1)
LOGSOFTMAX_FINAL = nn.LogSoftmax(dim=-1)
CROSSENT = nn.CrossEntropyLoss(reduction='none')

def token_gradients_with_output(model, input_ids, input_slice, target_slice, loss_slice):

    """
    Computes gradients of the loss with respect to the coordinates.

    Parameters
    ----------
    model : Transformer Model
        The transformer model to be used.
    input_ids : torch.Tensor
        The input sequence in the form of token ids.
    input_slice : slice
        The slice of the input sequence for which gradients need to be computed.
    target_slice : slice
        The slice of the input sequence to be used as targets.
    loss_slice : slice
        The slice of the logits to be used for computing the loss.

    Returns
    -------
    torch.Tensor
        The gradients of each token in the input_slice with respect to the loss.
    """
    embed_weights = list(model.modules())[2]
    assert type(embed_weights).__name__=='Embedding'
    embed_weights = embed_weights.weight
    one_hot = torch.zeros(
        input_ids[input_slice].shape[0],
        embed_weights.shape[0],
        device=model.device,
        dtype=embed_weights.dtype
    )
    one_hot.scatter_(
        1,
        input_ids[input_slice].unsqueeze(1),
        torch.ones(one_hot.shape[0], 1, device=model.device, dtype=embed_weights.dtype)
    )
    one_hot.requires_grad_()
    input_embeds = (one_hot @ embed_weights).unsqueeze(0)

    # now stitch it together with the rest of the embeddings
    embeds = model.get_input_embeddings()(input_ids.unsqueeze(0)).detach()
    full_embeds = torch.cat(
        [
            embeds[:,:input_slice.start,:],
            input_embeds,
            embeds[:,input_slice.stop:,:]
        ],
        dim=1)

    logits = model(inputs_embeds=full_embeds).logits
    targets = input_ids[target_slice]
    loss = nn.CrossEntropyLoss()(logits[0,loss_slice,:], targets)

    loss.backward()

    return one_hot.grad.clone(), logits.detach().clone()


class PromptOptimizer:
    """
    Implementation of Default GCG method, using the default
    settings from the paper (https://arxiv.org/abs/2307.15043v1)
    """

    def __init__(
        self,
        model: AutoModelForCausalLM,
        tokenizer: AutoTokenizer,
        n_proposals: int = 128,
        n_epochs: int = 500,
        n_top_indices: int = 256,
        prefix_loss_weight: float = 0,
        verbose: bool = False,
    ):

        self.model = model
        self.tokenizer = tokenizer
        self.n_proposals = n_proposals
        self.n_epochs = n_epochs
        self.n_top_indices = n_top_indices
        self.prefix_loss_weight = prefix_loss_weight
        self.verbose = verbose

    def calculate_restricted_subset(
        self,
        input_ids,
        input_slice,
        target_slice,
        loss_slice
    ):
        # Find the subset of tokens that have the most impact on the likelihood of the target
        grad,_ = token_gradients_with_output(self.model, input_ids, input_slice, target_slice, loss_slice)
        top_indices = torch.topk(-grad, self.n_top_indices, dim=-1).indices
        top_indices = top_indices.detach().cpu().numpy()
        return top_indices

    def sample_proposals(
        self,
        input_ids,
        top_indices,
        input_slice,
        target_slice,
        loss_slice,
        temperature = None
    ):
        # Sample random proposals
        proposals = []
        if temperature:
            logits = self.model(input_ids.view(1, *input_ids.shape)).logits
            probs = SOFTMAX_FINAL(logits/temperature) #from utils
        for p in range(self.n_proposals):
            if temperature:
                token_pos = np.random.randint(input_slice.start, input_slice.stop)
                rand_token = torch.multinomial(probs[0, token_pos, :], 1).item()
            else:
                token_pos = np.random.randint(input_slice.start, input_slice.stop)
                rand_token = np.random.choice(top_indices[token_pos-input_slice.start])
            prop = input_ids.clone()
            prop[token_pos] = rand_token
            proposals.append(prop)
        return torch.stack(proposals)

    def optimize(
        self,
        dialogue_preamble,
        initial_input,
        connecting_string,
        target_string,
        use_prefix_loss=False,
        temperature=0,
        early_stop=0.05
    ):
        # Parse input strings into tokens
        preamble_tokens = self.tokenizer.encode(dialogue_preamble, return_tensors="pt", add_special_tokens=False)[0].cuda()
        initial_inputs = self.tokenizer.encode(initial_input, return_tensors="pt", add_special_tokens=False)[0].cuda()
        connecting_tokens = self.tokenizer.encode(connecting_string, return_tensors="pt", add_special_tokens=False)[0].cuda()
        initial_targets = self.tokenizer.encode(target_string, return_tensors="pt", add_special_tokens=False)[0].cuda()

        input_ids = torch.cat([preamble_tokens, initial_inputs, connecting_tokens, initial_targets], dim=0)
        input_slice = slice(preamble_tokens.shape[0], preamble_tokens.shape[0] + initial_inputs.shape[0])
        target_slice = slice(preamble_tokens.shape[0]+initial_inputs.shape[0]+connecting_tokens.shape[0], input_ids.shape[-1])
        loss_slice = slice(preamble_tokens.shape[0]+initial_inputs.shape[0]+connecting_tokens.shape[0]-1, input_ids.shape[-1] - 1)

        # Shifted input slices for prefix loss calculation
        # shifted1 = slice(0, initial_inputs.shape[0] - 1)
        # shifted2 = slice(1, initial_inputs.shape[0])
        # Optimize input
        prev_loss = None
        for i in tqdm(range(self.n_epochs)):
            # if self.verbose and i==0 or i==10:
            #     print(f'whole input: {self.tokenizer.decode(input_ids)}')
            #     print(f'input slice: {self.tokenizer.decode(input_ids[input_slice])}')
            #     print(f'target slice: {self.tokenizer.decode(input_ids[target_slice])}')
            #     print(f'loss slice: {self.tokenizer.decode(input_ids[loss_slice])}')
            # Get proposals for next string
            top_indices = self.calculate_restricted_subset(input_ids, input_slice, target_slice, loss_slice)
            proposals = self.sample_proposals(input_ids, top_indices, input_slice, target_slice, loss_slice, temperature=temperature)
            # Choose the proposal with the lowest loss
            with torch.no_grad():
                prop_logits = self.model(proposals).logits
                targets = input_ids[target_slice]
                losses = [nn.CrossEntropyLoss()(prop_logits[pidx, loss_slice, :], targets).item() for pidx in range(prop_logits.shape[0])]
                if use_prefix_loss: # Add a penalty for unlikely prompts that are not very high-likelihood
                    raise NotImplementedError
                    # shifted_inputs = input_ids[shifted2]
                    # prefix_losses = [nn.CrossEntropyLoss()(prop_logits[pidx, shifted1, :], shifted_inputs).item() for pidx in range(prop_logits.shape[0])]
                    # losses = [losses[i] + self.prefix_loss_weight * prefix_losses[i] for i in range(len(losses))]
                # Choose next prompt
                new_loss = min(losses)
                min_idx = np.array(losses).argmin()
                if prev_loss is None or new_loss < prev_loss:
                    input_ids = proposals[min_idx]
                    prev_loss = new_loss
            if self.verbose and i % 5 ==0:
                print(f"Loss: {prev_loss:.2f} | {self.tokenizer.decode(input_ids)}")
            if prev_loss < early_stop:
                print(f'Early stopping from low loss')
                break
        return self.tokenizer.decode(input_ids), self.tokenizer.decode(input_ids[input_slice]), prev_loss


class autoDAN:
    """
    AutoDAN c.f. https://openreview.net/pdf?id=rOiymxm8tQ
    """

    def __init__(
        self,
        model: AutoModelForCausalLM,
        tokenizer: AutoTokenizer,
        batch: int = 256,
        split_batch: int = 1,
        max_steps: int = 500,
        weight_1: float = 3,
        weight_2: float = 100,
        temperature: float = 1,
        fwd_model: AutoModelForCausalLM = None,
        topk: bool = True,
    ):

        self.model = model
        self.tokenizer = tokenizer
        self.batch = batch
        self.split_batch = split_batch
        assert self.batch % self.split_batch == 0, "Batch size must be divisible by split_batch size"
        self.mini_batch = self.batch // self.split_batch
        self.weight_1 = weight_1
        self.weight_2 = weight_2
        self.temperature = temperature
        self.max_steps = max_steps
        if fwd_model is None:
            self.fwd_model = self.model
        else:
            self.fwd_model = fwd_model
        self.topk = topk


    def sample_model(
        self,
        input_ids,
    ):
        logits = self.fwd_model(input_ids).logits[:, -1, :]
        probs = SOFTMAX_FINAL(logits/self.temperature)
        samples = torch.multinomial(probs, 1)
        return samples
    

    def optimize(
        self,
        user_query,
        num_tokens,
        target_string,
        connection_tokens=torch.tensor([]),
        stop_its=1,
        verbose=False,
    ):
        '''
        user_query: string, query to be used as input to model. Should include BOS token (in string form) and chat dialogue preamble
        connection_tokens: tensor of tokens to be used as connection tokens for e.g. dialogue. Usually length 0 tensor for base LMs (must not have BOS token)
        
        Use stop_its to avoid early stopping with small batch sizes
        Note BOS token and custom dialogue templates not implemented yet
        Possible problem: tokenization iteratively adds tokens as characters, but these may be tokenized differently after addition
        '''
        query = self.tokenizer.encode(user_query, return_tensors="pt", add_special_tokens=False)[0].cuda()
        query_len = query.shape[-1]
        targets = self.tokenizer.encode(target_string, return_tensors="pt", add_special_tokens=False)[0].cuda()
        batch_targets = targets.unsqueeze(0).repeat(self.batch,1).contiguous().cpu()

        initial_x = self.sample_model(query.unsqueeze(0))[0]
        input_ids = torch.cat([query, initial_x, connection_tokens, targets], dim=0)
        adversarial_sequence = []
        adversarial_seq_tensor = torch.tensor(adversarial_sequence,dtype=torch.long).cuda()

        for ind in range(num_tokens): #iteratively construct adversarially generated sequence
            curr_token = query_len + ind
            optimized_slice = slice(curr_token, curr_token+1)
            target_slice = slice(curr_token + 1 + len(connection_tokens), input_ids.shape[-1])
            loss_slice = slice(curr_token + len(connection_tokens), input_ids.shape[-1] - 1)
            # print(f"slices: optimized slice {optimized_slice}, target slice {target_slice}, loss slice {loss_slice}")
            best_tokens = set()
            if verbose:
                print(f"For seq #{self.tokenizer.decode(input_ids)}#")
                print(f"Optimizing token {ind} at index {curr_token}: {self.tokenizer.decode(input_ids[curr_token])}")
            stop = 0
            for step in tqdm(range(self.max_steps)): #optimize current token
                grads, logits = token_gradients_with_output(self.model, input_ids, optimized_slice, target_slice, loss_slice)
                with torch.no_grad():
                    curr_token_logprobs = LOGSOFTMAX_FINAL(self.fwd_model(input_ids[:curr_token].unsqueeze(0))['logits'][0,-1,:]) # LOGSOFTMAX_FINAL(logits[0, curr_token-1, :])
                    scores = -1*self.weight_1*grads+curr_token_logprobs
                    if self.topk: candidate_tokens = torch.topk(scores, self.batch-1, dim=-1).indices.detach()
                    else: candidate_tokens = torch.multinomial(SOFTMAX_FINAL(scores/self.temperature), self.batch-1).detach()
                    candidate_tokens = torch.cat((candidate_tokens[0],input_ids[curr_token:curr_token+1]),dim=0) #append previously chosen token
                    candidate_sequences = input_ids.unsqueeze(0).repeat(self.batch,1).contiguous()
                    candidate_sequences[:,curr_token] = candidate_tokens
                    
                    all_logits = []
                    for b in range(self.split_batch):
                        all_logits.append(self.model(candidate_sequences[b*self.mini_batch:(b+1)*self.mini_batch,:]).logits.cpu())
                    all_logits = torch.cat(all_logits, dim=0)
                    loss_logits = all_logits[:, loss_slice, :].contiguous()
                    target_losses = CROSSENT(loss_logits.view(-1,loss_logits.size(-1)), batch_targets.view(-1)) #un-reduced cross-ent
                    target_losses = torch.mean(target_losses.view(self.batch,-1), dim=1) #keep only batch dimension
                    combo_scores = -1*self.weight_2*target_losses + curr_token_logprobs[candidate_tokens].cpu()
                    combo_probs = SOFTMAX_FINAL(combo_scores/self.temperature)
                    temp_token = candidate_tokens[torch.multinomial(combo_probs, 1)]
                    best_token = candidate_tokens[torch.argmax(combo_probs).item()]
                    int_best = int(best_token.item())
                if verbose:
                    print(f"max prob {torch.max(combo_probs):.2f} temp_token {self.tokenizer.decode(temp_token)} token_id {temp_token.item()} and best_token {self.tokenizer.decode(best_token)} token_id {best_token}")
                    print(f"10 candidate tokens at step {step}: {self.tokenizer.decode(candidate_tokens[:10])}")
                    print("Losses:")
                    print(f"     Initial loss at step {ind}, iteration {step}: {torch.max(-1*target_losses).item():.2f}")
                    print(f"     Combination scores at step {ind}, iteration {step}: {[round(val.item(),2) for val in torch.topk(combo_scores,5)[0]]}") #torch.topk(combo_scores,5)
                if int_best in best_tokens:
                    print(f'Token already chosen, stopping {stop+1} out of {stop_its}')
                    stop+=1
                    if stop==stop_its:
                        # if verbose:
                        print("Losses:")
                        print(f"     Final loss at step {ind}, iteration {step}: {torch.max(-1*target_losses).item():.2f}")
                        print(f"     Combination scores at step {ind}, iteration {step}: {[round(val.item(),2) for val in torch.topk(combo_scores,5)[0]]}") #torch.topk(combo_scores,5)
                        print(f"Best token {self.tokenizer.decode(best_token)} Sampled token {self.tokenizer.decode(temp_token)}")
                        adversarial_sequence.append(temp_token)
                        break
                if step==self.max_steps-1:
                    # if verbose:
                    print("Losses:")
                    print(f"     Final loss at step {ind}, iteration {step}: {torch.max(-1*target_losses).item():.2f}")
                    print(f"     Combination scores at step {ind}, iteration {step}: {[round(val.item(),2) for val in torch.topk(combo_scores,5)[0]]}") #torch.topk(combo_scores,5)
                    print(f"Best token {self.tokenizer.decode(best_token)}. Sampled token {self.tokenizer.decode(temp_token)}.")
                    adversarial_sequence.append(temp_token)
                    break
                best_tokens.add(int_best)
                input_ids = torch.cat([query, adversarial_seq_tensor, temp_token, connection_tokens, targets], dim=0)
            
            adversarial_seq_tensor = torch.tensor(adversarial_sequence,dtype=torch.long).cuda()
            next_in = torch.cat([query, adversarial_seq_tensor],dim=0).unsqueeze(0).type(torch.long)
            next_tok_rand = self.sample_model(next_in)[0]
            input_ids = torch.cat([query, adversarial_seq_tensor, next_tok_rand, connection_tokens, targets], dim=0)


        return self.tokenizer.decode(torch.tensor(adversarial_sequence)), torch.max(-1*target_losses).item()