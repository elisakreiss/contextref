import pandas as pd
import os
import argparse
from PIL import Image
from collections import defaultdict
import torch.nn.functional as F
import torch
from evaluators.blip_embed import BLIP_EmbedEvaluator, blip_embed_models
from evaluators.blip_language import BLIP_LanguageEvaluator, blip_language_models
from evaluators.clip_embed import CLIP_Evaluator, clip_models
from evaluators.flamingo_language import Flamingo_LanguageEvaluator, flamingo_language_models
from evaluators.frozen_language import Frozen_LanguageEvaluator, frozen_language_models

# Load the metric dataframe
overall_root = '../../data/'
csv_root = f'{overall_root}/train_data/csvs'
global_image_dir = f"{overall_root}/images/images_chunk0"
all_df_metrics = os.listdir(csv_root)
all_df_metrics = [metric_name for metric_name in all_df_metrics if metric_name.endswith('.csv')]
# put the one with "gold" in the front
all_df_metrics = sorted(all_df_metrics, key=lambda x: 0 if 'gold' in x else 1)

combined_dict = {
    'flamingo_language': (flamingo_language_models, Flamingo_LanguageEvaluator),
    'frozen_language': (frozen_language_models, Frozen_LanguageEvaluator),
    'clip': (clip_models, CLIP_Evaluator),
    'blip_embed': (blip_embed_models, BLIP_EmbedEvaluator),
    'blip_language': (blip_language_models, BLIP_LanguageEvaluator)
}

def sanitize_model_name(model_name):
    model_name = str(model_name)
    model_name = model_name.replace('/', '_')
    model_name = model_name.replace(' ', '_')
    # Remove all non-alphanumeric characters
    model_name = ''.join([c for c in model_name if c.isalnum() or c == '_'])
    return model_name

def run_model(model_name, cur_evaluator_name, gold_only=False, skip_existing=True, lr=2e-6, batch_size=64, epochs=0.1, mode="eval"):
    _, EvalClass = combined_dict[cur_evaluator_name]
    # Create a folder for the model, skip if it already exists
    sanitized_model_name = sanitize_model_name(model_name)
    if os.path.exists(f'{overall_root}/{results_folder_name}/{cur_evaluator_name}/{sanitized_model_name}') and skip_existing:
        # Check if there are any csvs in the folder
        files_in_folder = os.listdir(f'{overall_root}/{results_folder_name}/{cur_evaluator_name}/{sanitized_model_name}')
        if len(files_in_folder) > 0:
            if any([file.endswith('.csv') for file in files_in_folder]):
                print(f'{overall_root}/{results_folder_name}/{cur_evaluator_name}/{sanitized_model_name}')
                print(f'Skipping {model_name} because it was already evaluated.')
                return
    print("Evaluating", model_name)
    evaluator = EvalClass(model_name, lr=lr, batch_size=batch_size, epochs=epochs)
    os.makedirs(f'{overall_root}/{results_folder_name}/{cur_evaluator_name}/{sanitized_model_name}', exist_ok=True)
    gold_df_metric = pd.read_csv(f'{csv_root}/df_metric_gold.csv')
    image_names = {}
    df_metrics = {}
    for metric_name in all_df_metrics:
        # We treat gold metrics as the target when training
        if 'gold' in metric_name and mode == 'train':
            continue
        elif gold_only and 'gold' not in metric_name:
            continue
        df_metric = pd.read_csv(f'{csv_root}/{metric_name}')

        # For images, they will be in images_chunk0 unless 'frankenstein' is in the metric_name
        image_dir = global_image_dir
        if 'frankenstein' in metric_name:
            image_dir = global_image_dir + '_wdistractors'

        for image_name in os.listdir(image_dir):
            if image_name.endswith(".png") or image_name.endswith(".jpg") or image_name.endswith(".jpeg"):
                image_names[image_name] = Image.open(os.path.join(image_dir, image_name)).convert('RGB')

        df_metrics[metric_name] = df_metric
        if mode == 'eval':
            print(f'Evaluating {model_name} on {metric_name}')
            evaluator.eval(df_metric, image_names)
            # Save the new dataframe
            df_metric.to_csv(f'{overall_root}/{results_folder_name}/{cur_evaluator_name}/{sanitized_model_name}/{metric_name}', index=False)

    if mode == 'train':
        print(f'Training {model_name}')
        evaluator.train(df_metrics, image_names, gold_df_metric, image_names)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Specify type of evaluator and whether gold_only.')
    parser.add_argument('evaluator_type', type=str, help='The type of evaluator to use.')
    parser.add_argument('--gold_only', action='store_true',
                        help='Specify if only "gold" metrics are used.')
    parser.add_argument('--reverse', action='store_true',
                        help='Specify if only "gold" metrics are used.')
    parser.add_argument('--results_folder_name', type=str, default='results',
                        help='Specify the name of the results folder.')
    parser.add_argument('--mode', type=str, default='eval',
                        help='Specify the mode of the script. Either "eval" or "train".')
    args = parser.parse_args()

    cur_evaluator_name = args.evaluator_type
    if cur_evaluator_name not in combined_dict.keys():
        print(f'Invalid evaluator type. Please choose from {list(combined_dict.keys())}')
        exit()

    # Create a folder for the evaluator
    results_folder_name = args.results_folder_name
    os.makedirs(f'{overall_root}/{results_folder_name}/{cur_evaluator_name}', exist_ok=True)
    model_names, _ = combined_dict[cur_evaluator_name]
    epoch = 0.5
    if args.reverse:
        model_names = model_names[::-1]
    for model_name in model_names:
        try:
            run_model(model_name, cur_evaluator_name, args.gold_only, epochs=epoch, mode=args.mode)
        except Exception as e:
            print(f'Error with {model_name}: {e}')