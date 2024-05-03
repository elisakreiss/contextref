import torch
import torch.nn.functional as F
from collections import defaultdict
from tqdm.auto import tqdm
from functools import lru_cache
import random
import pandas as pd
import os
tqdm.pandas()

def sanitize_model_name(model_name):
    model_name = str(model_name)
    model_name = model_name.replace('/', '_')
    model_name = model_name.replace(' ', '_')
    # Remove all non-alphanumeric characters
    model_name = ''.join([c for c in model_name if c.isalnum() or c == '_'])
    return model_name

CONTEXT_TYPE = 'context'

class Evaluator:
    def __init__(self, model_name, image_prefix="", lr=1e-4, batch_size=256, epochs=1):
        self.model_name = model_name
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # If there are multiple GPUs, we want to use the last one for vision
        self.vision_device = torch.device(f'cuda:{torch.cuda.device_count() - 1}' if torch.cuda.is_available() else 'cpu')
        self.cache = defaultdict(dict)
        self.full_text_format = "{base_text} {target_text}"
        self.initialize_model(model_name)
        # self.lr = 4e-7 # For embedding model[[s
        print(f"Using lr {lr}, batch size {batch_size}, epochs {epochs}")
        self.lr = lr # For embedding models
        # self.lr = 1e-2 # For language models
        self.loss = torch.nn.BCEWithLogitsLoss()
        self.batch_size = batch_size
        self.epochs = epochs

    def embed_image(self, image):
        raise NotImplementedError()
    
    def embed_text(self, text):
        raise NotImplementedError()
    
    def text_logprob(self, text):
        raise NotImplementedError()

    # @lru_cache(maxsize=None)
    def clipscore(self, image_name, text, context):
        features_image = F.normalize(self.embed_image(image_name))
        features_text = F.normalize(self.embed_text(text))
        assert len(features_image.shape) == 2
        assert len(features_text.shape) == 2
        score = (features_image @ features_text.t()).max(dim=-2)[0].item()
        return score

    # @lru_cache(maxsize=None)
    def contextscore(self, image_name, text, context, return_tensor=False):
        embed_image = self.embed_image(image_name)
        embed_text = self.embed_text(text)
        embed_context = self.embed_text(context)

        assert len(embed_image.shape) == 2
        assert len(embed_text.shape) == 2
        assert len(embed_context.shape) == 2
        p1 = F.normalize(embed_text, dim=-1) @ embed_context.t()
        p2 = (embed_text @ (F.normalize(embed_image, dim=-1) - F.normalize(embed_context, dim=-1)).t()).t()
        sim = p1 + torch.max(p2, dim=-2)[0]
        if return_tensor:
            return sim
        score = sim.item()
        return score
    
    # @lru_cache(maxsize=None)
    def text_if_good(self, image_name, text, context, reduce=False, diff=True, return_tensor=False):
        base_text = ""
        if context is not None:
            base_text += f'[Context: {context}] '
        base_text += 'High quality, accessible, image description:'
        target_text = text
        score = self.score_fn(image_name, base_text, target_text, reduce=reduce, diff=diff, return_tensor=return_tensor)
        return score
    
    # @lru_cache(maxsize=None)
    def good_if_text(self, image_name, text, context, reduce=False, diff=True, return_tensor=False):
        base_text = ""
        if context is not None:
            base_text += f'[Context: {context}] '
            base_text += 'Look at the context, photo, and description and rate the description from 1-5 based on whether it is a high quality, accessible, image description. Description:'
        else:
            base_text += 'Look at the photo and description and rate the description from 1-5 based on whether it is a high quality, accessible, image description. Description:'
        target_text = '5'
        score = self.score_fn(image_name, base_text, target_text, reduce=reduce, diff=diff)
        return score

    # @lru_cache(maxsize=None)
    def score_fn(self, image_name, base_text, target_text, reduce=False, diff=True, return_tensor=False):
        full_text = self.full_text_format.format(base_text=base_text, target_text=target_text)
        tokens_full = len(self.tokenizer(full_text)['input_ids'])
        tokens_base = len(self.tokenizer(base_text)['input_ids'])
        scale = 1
        if reduce:
            scale = (tokens_full - tokens_base) if diff else tokens_full
        full_score = self.get_score(image_name, full_text)
        base_score = self.get_score(image_name, base_text) if diff else 0
        final_score = -(full_score - base_score) / scale
        if return_tensor:
            return final_score
        return final_score.item()

    def score_df(self, df_metric, model_col, human_col='q_overall.postimg', desc_col='descr_original'):
        grouped = df_metric.groupby(desc_col)[[model_col, human_col]].mean()
        # also return the average score by the model
        return grouped[model_col].corr(grouped[human_col]), grouped[model_col].mean()

    def train_embeds(self, df_metric, image_names, mode="contextscore", regularize=False):
        acc_counter = 0
        if mode == "clipscore":
            df_metric['clipscore'] = df_metric.progress_apply(
                lambda x: self.clipscore(x['img_id'], x['description'], x[CONTEXT_TYPE]), axis=1)
            print(f"Correlation between CLIP score and human ratings: {self.score_df(df_metric, 'clipscore')}")
        elif mode == "contextscore":
            # Iterate over df_metric
            total_seen = 0
            while total_seen < self.epochs * df_metric.shape[0]:
                df_metric = df_metric.sample(frac=1)
                remaining_in_epoch = min(self.epochs * df_metric.shape[0] - total_seen, df_metric.shape[0])
                for index, row in tqdm(df_metric.iterrows(), total=remaining_in_epoch):
                    diff, score, gold_score = self.get_diff(row, self.contextscore, return_scores=True)
                    gold_score = self.model_to_human_multiplier * gold_score + self.model_to_human_bias
                    target_gold_score = row['q_overall.postimg']
                    total_seen += 1
                    if diff != diff:
                        print(f"NaN score for {image_name} {text} {context}")
                        continue
                    diff = self.loss(diff, torch.zeros_like(diff))
                    if regularize:
                        diff = diff + (gold_score - base_gold_score.detach()) ** 2
                    diff = diff / self.batch_size
                    diff.backward()
                    acc_counter += 1
                    if acc_counter % self.batch_size == 0 or total_seen >= self.epochs * df_metric.shape[0]:
                        self.optimizer.step()
                        self.optimizer.zero_grad()
                    if total_seen >= self.epochs * df_metric.shape[0]:
                        break

    def train_language(self, df_metric, image_names, mode="contextscore"):
        acc_counter = 0
        if mode == "clipscore":
            df_metric['clipscore'] = df_metric.apply(
                lambda x: self.clipscore(x['img_id'], x['description'], x[CONTEXT_TYPE]), axis=1)
            print(f"Correlation between CLIP score and human ratings: {self.score_df(df_metric, 'clipscore')}")
        elif mode == "contextscore":
            # Iterate over df_metric
            step_losses = []
            total_seen = 0
            while total_seen < self.epochs * df_metric.shape[0]:
                df_metric = df_metric.sample(frac=1)
                remaining_in_epoch = min(self.epochs * df_metric.shape[0] - total_seen, df_metric.shape[0])
                for index, row in tqdm(df_metric.iterrows(), total=remaining_in_epoch):
                # for index, row in df_metric.iterrows():
                    score_fn = lambda image_name, text, context, return_tensor=True, use_context=True, reduce=True, diff=False: self.text_if_good(
                        image_name, text, context if use_context else None, reduce=reduce, diff=diff, return_tensor=return_tensor
                    )
                    # diff = self.get_diff(row, score_fn)
                    diff, score, gold_score = self.get_diff(row, score_fn, return_scores=True)
                    total_seen += 1
                    if diff != diff:
                        print(f"NaN score for {image_name} {text} {context}")
                        continue
                    diff = self.loss(diff, torch.zeros_like(diff))
                    gold_score = self.model_to_human_multiplier * gold_score + self.model_to_human_bias
                    target_gold_score = row['q_overall.postimg']
                    diff = diff + (gold_score - target_gold_score) ** 2 / 5
                    diff = diff / self.batch_size
                    with torch.no_grad():
                        step_losses.append(diff.item())
                    diff.backward()
                    acc_counter += 1
                    if acc_counter % self.batch_size == 0 or total_seen >= self.epochs * df_metric.shape[0]:
                        self.optimizer.step()
                        self.optimizer.zero_grad()
                        print(f"Loss: {sum(step_losses) / len(step_losses)}")
                        step_losses = []
                    if total_seen >= self.epochs * df_metric.shape[0]:
                        break

    def get_diff(self, row, score_fn, return_scores=False, base_model_score=False):
        # Get image name
        image_name = row['img_id']
        # Get description
        text = row['description']
        # Get context
        context = row[CONTEXT_TYPE]
        # Get score
        score = score_fn(image_name, text, context, return_tensor=True)
        
        # Find a row in self.gold_df_metric with the same description
        gold_row = self.gold_df_metric.loc[
            self.gold_df_metric['description'] == row['descr_original']]

        # Make sure that the split is the same
        gold_row = gold_row.loc[gold_row['split'] == row['split']]
        # Choose a random one if there are multiple
        gold_row = gold_row.sample(n=1)
        gold_text = gold_row['description'].values[0]
        # Get the image name
        gold_image_name = gold_row['img_id'].values[0]
        # Get the context
        gold_context = gold_row[CONTEXT_TYPE].values[0]
        # Get the score
        gold_score = score_fn(gold_image_name, gold_text, gold_context, return_tensor=True)
        if base_model_score:
            self.true_model = self.model
            self.model = self.base_model
            base_gold_score = score_fn(gold_image_name, gold_text, gold_context, return_tensor=True)
            self.model = self.true_model
        diff = score - gold_score
        if return_scores:
            if base_model_score:
                return diff, score, gold_score, base_gold_score
            return diff, score, gold_score
        return diff


    def eval_embeds(self, df_metric, image_names):
        with torch.no_grad():
            df_metric['contextscore'] = df_metric.apply(
                lambda x: self.contextscore(x['img_id'], x['description'], x[CONTEXT_TYPE]), axis=1)
            print(f"Correlation between contextscore and human ratings: {self.score_df(df_metric, 'contextscore')}")
            if not hasattr(self, 'gold_df_metric'):
                return
            attempts = 0
            corrects = 0
            equals = 0
            for index, row in tqdm(df_metric.iterrows(), total=df_metric.shape[0]):
                diff = self.get_diff(row, self.contextscore)
                if diff < 0:
                    corrects += 1
                if diff <= 0:
                    equals += 1
                attempts += 1
            print(f"Accuracy of contextscore: {corrects / attempts}, <= 0: {equals / attempts}")

    def eval_language(self, df_metric, image_names):
        methods = {
            'text_if_good': self.text_if_good,
        }
        use_context = True
        reduce = True
        diff = False
        with torch.no_grad():
            for method in methods:
                name_addition = ""
                if not use_context:
                    name_addition += "_no_context"
                if reduce:
                    name_addition += "_reduce"
                if diff:
                    name_addition += "_diff"
                col = f"p_{method}{name_addition}"
                df_metric[col] = df_metric.progress_apply(
                    lambda x: methods[method](
                        x['img_id'], x['description'], x[CONTEXT_TYPE] if use_context else None, reduce=reduce, diff=diff
                    ), axis=1)
                print(f"Correlation between {col} and human ratings: {self.score_df(df_metric, col)}")
                if not hasattr(self, 'gold_df_metric'):
                    return

                attempts = 0
                corrects = 0
                equals = 0
                for index, row in df_metric.iterrows():
                    score_fn = lambda image_name, text, context, return_tensor=True: self.text_if_good(
                        image_name, text, context if use_context else None, reduce=reduce, diff=diff, return_tensor=return_tensor
                    )
                    diff = self.get_diff(row, score_fn)
                    if diff < 0:
                        corrects += 1
                    if diff <= 0:
                        equals += 1
                    attempts += 1
                print(f"Accuracy of contextscore: {corrects / attempts}, <= 0: {equals / attempts}")

    def pre_eval_hook(self, df_metric, image_names):
        pass

    def eval(self, df_metric, image_names):
        self.image_name_map = image_names
        self.pre_eval_hook(df_metric, image_names)
        if 'embed' in self.modes:
            self.eval_embeds(df_metric, image_names)
        if 'language' in self.modes:
            self.eval_language(df_metric, image_names)

    def train(self, df_metrics, image_names, gold_df_metric, base_image_names, pre_eval=False, save_csv=True):
        df_sizes = {df_metric_name: len(df_metric) for df_metric_name, df_metric in df_metrics.items()}
        print(f"Training on {df_sizes} samples")
        self.image_name_map = image_names
        # self.gold_image_name_map = base_image_names
        self.gold_df_metric = gold_df_metric
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        # Save CSV
        if save_csv and pre_eval:
            self.pre_eval_hook(gold_df_metric, image_names)
            df_list = list(df_metrics.items())
            df_list.insert(0, ('df_metric_gold', gold_df_metric))
            for df_metric_name, df_metric in df_list:
                if ".csv" in df_metric_name:
                    df_metric_name = df_metric_name.replace(".csv", "")
                if 'embed' in self.modes:
                    df_metric['contextscore'] = df_metric.progress_apply(
                        lambda x: self.contextscore(x['img_id'], x['description'], x[CONTEXT_TYPE]), axis=1)
                if 'language' in self.modes:
                    df_metric['p_text_if_good'] = df_metric.progress_apply(
                        lambda x: self.text_if_good(x['img_id'], x['description'], x[CONTEXT_TYPE], reduce=True, diff=False), axis=1)
                # Make a directory for the current model
                dir_name = sanitize_model_name(self.model_name) + "_train"
                os.makedirs(dir_name, exist_ok=True)
                df_metric.to_csv(f"{dir_name}/{df_metric_name}_beforetraining.csv", index=False)

        train_dfs = {}
        test_dfs = {}
        for df_metric_name, df_metric in df_metrics.items():
            # Shuffle
            df_metric_shuffled = df_metric.sample(frac=1)
            # Split into train and test
            if 'split' in df_metric_shuffled:
                train_dfs[df_metric_name] = df_metric_shuffled[df_metric_shuffled['split'] == 'train']
                test_dfs[df_metric_name] = df_metric_shuffled[df_metric_shuffled['split'] == 'test']
            else:
                train_dfs[df_metric_name] = df_metric_shuffled.iloc[:int(df_metric_shuffled.shape[0] * 0.8)]
                test_dfs[df_metric_name] = df_metric_shuffled.iloc[int(df_metric_shuffled.shape[0] * 0.8):]
        train_df_sizes = {df_metric_name: df.shape[0] for df_metric_name, df in train_dfs.items()}
        combined_df_metric = pd.concat(train_dfs.values())
        # Shuffle
        combined_df_metric = combined_df_metric.sample(frac=1)

        test_gold_df_metric = gold_df_metric[gold_df_metric['split'] == 'test']
        print("Evaluating test split of gold df_metric before training...")
        self.pre_eval_hook(test_gold_df_metric, image_names)
        self.eval(test_gold_df_metric, image_names)
        train_gold_df_metric = gold_df_metric[gold_df_metric['split'] == 'train']
        human_mean = train_gold_df_metric['q_overall.postimg'].mean()
        human_std = train_gold_df_metric['q_overall.postimg'].std()
        
        print("Evaluating train split of gold df_metric before training...")
        self.eval(train_gold_df_metric, image_names)
        if 'contextscore' in train_gold_df_metric:
            model_metric = 'contextscore'
        else:
            model_metric = 'p_text_if_good_reduce'
        model_mean = train_gold_df_metric[model_metric].mean()
        model_std = train_gold_df_metric[model_metric].std()
        model_to_human_multiplier = human_std / model_std
        model_to_human_bias = human_mean - model_mean * model_to_human_multiplier
        self.model_to_human_multiplier = model_to_human_multiplier
        self.model_to_human_bias = model_to_human_bias

        if pre_eval:    
            for df_metric_name, df_metric in sorted(list(test_dfs.items())):
                print(f"Evaluating {df_metric_name} before training...")
                self.pre_eval_hook(df_metric, image_names)
                self.eval(df_metric, image_names)

        self.pre_eval_hook(combined_df_metric, image_names)
        print("Training...")
        if 'embed' in self.modes:
            self.train_embeds(combined_df_metric, image_names)
        if 'language' in self.modes:
            self.train_language(combined_df_metric, image_names)

        # Also evaluate the gold df_metric
        self.pre_eval_hook(gold_df_metric, image_names)
        gold_df_metric_eval = gold_df_metric[gold_df_metric['split'] == 'test']
        self.eval(gold_df_metric_eval, image_names)

        for df_metric_name, df_metric in sorted(list(test_dfs.items())):
            print(f"Evaluating {df_metric_name} after training...")
            # Only evaluate the test set
            self.eval(df_metric, image_names)

        # Save CSV
        if save_csv:
            df_list = list(df_metrics.items())
            df_list.insert(0, ('df_metric_gold', gold_df_metric))
            for df_metric_name, df_metric in df_list:
                if ".csv" in df_metric_name:
                    df_metric_name = df_metric_name.replace(".csv", "")
                self.pre_eval_hook(df_metric, image_names)
                if 'embed' in self.modes:
                    df_metric['contextscore'] = df_metric.progress_apply(
                        lambda x: self.contextscore(x['img_id'], x['description'], x[CONTEXT_TYPE]), axis=1)
                if 'language' in self.modes:
                    df_metric['p_text_if_good'] = df_metric.progress_apply(
                        lambda x: self.text_if_good(x['img_id'], x['description'], x[CONTEXT_TYPE], reduce=True, diff=False), axis=1)
                dir_name = sanitize_model_name(self.model_name) + "_train"
                os.makedirs(dir_name, exist_ok=True)
                epochs_str = f"epochs_{self.epochs}".replace(".", "_")
                df_metric.to_csv(f"{dir_name}/{df_metric_name}_aftertraining_{epochs_str}.csv", index=False)
