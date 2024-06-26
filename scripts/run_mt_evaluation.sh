!/bin/bash

base_path=/scratch/alc9734/latent-adversarial-training/results ;
# for c in 1000 4000 16000; do
# for m in ${base_path}/run_large_scale_concept_1/checkpoint-${c} ; do sbatch submit_mt.sh $m large_scale_concept_$c ; done
# for m in ${base_path}/run_persuasion_0.5/checkpoint-${c} ; do sbatch submit_mt.sh $m persuasion_0.5_$c ; done;
# for m in ${base_path}/run_no_steer_full/checkpoint-${c} ; do sbatch submit_mt.sh $m no_steer_$c ; done;
# for m in ${base_path}/run_2/checkpoint-${c} ; do sbatch submit_mt.sh $m refusal_$c ; done;
# done

# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-7b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat7b ; done;
# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-13b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat13b ; done;

# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-7b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat7b steering mean "1" ; done;
# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-7b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat7b steering mean "2" ; done;
# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-7b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat7b steering mean "3" ; done;
# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-7b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat7b steering pca_unnorm ; done;

# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-7b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat7b steering last_20 ; done;
# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-7b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat7b steering ; done;
# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-13b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat13b steering ; done;
# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-13b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat13b steering mean ; done;
# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-13b-chat-hf ; do sbatch submit_mt.sh $m llama-2-chat13b steering last_20 ; done;
# for m in ${base_path}/run2_persuasion_0.5 ; do sbatch submit_mt.sh $m persuasion_0.5 ; done;
# for m in ${base_path}/run2_persuasion_0.5 ; do sbatch submit_mt.sh $m persuasion_0.5 steering ; done;
# for m in ${base_path}/run2_no_steer ; do sbatch submit_mt.sh $m no_steer steering ; done;
# for m in ${base_path}/run2_no_steer ; do sbatch submit_mt.sh $m no_steer steering ; done;

# for f in 0.125 0.25 0.5 ; do
# for m in ${base_path}/run2_working_concepts_${f} ; do sbatch submit_mt.sh $m working_concepts_${f} ; done;
# for m in ${base_path}/run2_persuasion_working_concepts_${f} ; do sbatch submit_mt.sh $m persuasion_working_concepts_${f} ; done;
# for m in ${base_path}/run2_working_concepts_${f} ; do sbatch submit_mt.sh $m working_concepts_${f} steering ; done;
# for m in ${base_path}/run2_persuasion_working_concepts_${f} ; do sbatch submit_mt.sh $m persuasion_working_concepts_${f} steering ; done;
# for m in ${base_path}/run2_working_concepts_${f}_buffer_30/checkpoint-12000 ; do for e in refusal ; do sbatch submit_eval.sh $m $e /scratch/alc9734/latent-adversarial-training/datasets/ big ; done; done ;
# done

# for l in run2_lora_no_steer run2_lora_persuasion_0.5 run2_lora_persuasion_working_concepts_0.5 run2_lora_working_concepts_0.5 ; do
# for l in  run2_ppo_no_steer_lr1e-4 ; do
# for l in run2_lora_working_concepts_0.5_range-1,1 run2_lora_large_scale_concept_0.5_range-1,1 run2_lora_kl_large_scale_concept_0.5 run2_lora_working_concepts_0.5_noisytune ; do
# for l in run2_lora_kl_large_scale_concept_0.5 run2_lora_working_concepts_0.5_noisytune ; do
# for l in run2_ppo_working_concepts_0.5 ; do
# for l in run2_ppo_working_concepts_0.5 run2_lora_kl_lr_1e-5_working_concepts_0.5 run2_lora_kl_lr_1e-5_large_scale_concept_0.5 run2_lora_kl_lr_5e-5_working_concepts_0.5 run2_lora_kl_lr_5e-5_large_scale_concept_0.5 run2_lora_kl_lr_1e-5_working_concepts_0.125 run2_lora_kl_lr_1e-5_large_scale_concept_0.125 run2_lora_kl_lr_5e-5_working_concepts_0.125 run2_lora_kl_lr_5e-5_large_scale_concept_0.125 ; do
# for l in run2_ppo_persuasion_refusal0.50 ; do
# for d in refusal_data_full_answers refusal_data_A_B_cropped refusal_data_A_B_question_pairs ; do
# for d in refusal_data_A_B_cropped_jinja_augmented refusal_data_full_answers_jinja_augmented refusal_data_A_B_cropped_jinja_augmented_v2 refusal_data_full_answers_jinja_augmented_v2 ; do
# for l in run2_lora_kl_lr_1e-5_15_large_scale_concept_0.0_mean run2_lora_kl_lr_1e-5_15_large_scale_concept_0.125_mean run2_lora_kl_lr_1e-5_15_working_concepts_0.0_mean run2_lora_kl_lr_1e-5_15_working_concepts_0.125_mean ; do
# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-7b-chat-hf ; do
#   sbatch submit_mt.sh $m $l lora mean ${base_path}/${l} $d;
#   done
# done;
# done
# for d in refusal_data_A_B_cropped refusal_data_full_answers ; do
for d in filtered_questions_style_question_pairs ; do
# for d in bias_mmlu_suggested_answer bias_logiqa_suggested_answer bias_hellaswag_suggested_answer bias_truthfulqa_suggested_answer ; do
for l in run2_lora_dpo_50_ep4 run2_lora_dpo_50_batch_lr_5e-5 run2_lora_dpo_50_batch run2_lora_kl_lr_1e-5_15_large_scale_concept_0.125_mean run2_lora_kl_lr_1e-5_15_working_concepts_0.125_mean ; do
for m in /vast/work/public/ml-datasets/llama-2/Llama-2-7b-chat-hf ; do
  sbatch submit_mt.sh $m $l lora mean ${base_path}/${l} $d;
  done
done;
done

# for d in refusal_data_full_answers refusal_data_A_B_cropped refusal_data_A_B_question_pairs filtered_questions_style_question_pairs refusal_data_A_B_cropped_jinja_augmented refusal_data_full_answers_jinja_augmented; do
# for l in run2_lora_kl_lr_5e-5_large_scale_concept_0.0_pca run2_lora_kl_lr_5e-5_large_scale_concept_0.125_pca run2_lora_kl_lr_5e-5_working_concepts_0.0_pca run2_lora_kl_lr_5e-5_working_concepts_0.125_pca ; do
# for m in /vast/work/public/ml-datasets/llama-2/Llama-2-7b-chat-hf ; do
#   sbatch submit_mt.sh $m $l lora pca_unnorm ${base_path}/${l} $d;
#   done
# done;
# done
