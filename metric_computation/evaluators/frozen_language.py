from evaluator import Evaluator
from functools import lru_cache
from transformers import GPTJForCausalLM, AutoTokenizer, GPT2LMHeadModel, AutoModelForCausalLM, GPT2Tokenizer
import torch
import open_clip
import deepspeed
# ordereddict
from collections import OrderedDict
from frozen_list_of_words import filtered_words
import spacy
# download en_core_web_sm
nlp = spacy.load("en_core_web_sm")

language_models = [
    'facebook/opt-350m',
    'facebook/opt-1.3b',
    'facebook/opt-2.7b',
    'facebook/opt-6.7b',
    'facebook/opt-13b',
    'EleutherAI/gpt-j-6B',
    'gpt2-large',
    'gpt2-xl',
]

clip_models = [
    ("ViT-B-32", "openai"),
    ("RN50x4", "openai"),
    ("convnext_xxlarge", "laion2b_s34b_b82k_augreg"),
    ("ViT-bigG-14", "laion2b_s39b_b160k"),
    ("coca_ViT-L-14", "laion2b_s13b_b90k"),
    ("roberta-ViT-B-32", "laion2b_s12b_b32k"),
    ("EVA02-E-14-plus", "laion2b_s9b_b144k")
]

frozen_language_models = [
    (clip_model, language_model) for clip_model in clip_models for language_model in language_models
]

n_image_toks = 50
toks = [f'<img{x}>' for x in range(n_image_toks)]

def get_tokenizer(model_name):
    if "llama" in model_name:
        from transformers import LlamaTokenizer as Tokenizer
    else:
        Tokenizer = AutoTokenizer
    tokenizer = Tokenizer.from_pretrained(model_name)
    return tokenizer

class Frozen_LanguageEvaluator(Evaluator):
    def initialize_model(self, full_model_name):
        clip_model_name, gpt_model_name = full_model_name
        self.clip_model_name = clip_model_name
        self.gpt_model_name = gpt_model_name
        self.tokenizer = get_tokenizer(gpt_model_name)
        self.tokenizer._add_tokens(toks)
        tokenizer = self.tokenizer
        self.clip_tokenizer = open_clip.get_tokenizer(clip_model_name[0])
        device = self.device
        self.char = ''
        if gpt_model_name == "gpt2-large" or gpt_model_name == "gpt2-xl":
            gpt2 = GPT2LMHeadModel.from_pretrained(gpt_model_name, pad_token_id=tokenizer.eos_token_id).to(device)
            gpt2.to(device)
            gpt2_transformer = gpt2.transformer
            model_embeddings = gpt2_transformer.wte.weight
            self.char = 'Ġ'
        elif gpt_model_name == "EleutherAI/gpt-j-6B":
            gpt2 = GPTJForCausalLM.from_pretrained("EleutherAI/gpt-j-6B", revision="float16", load_in_8bit=True, device_map="auto")
            device = gpt2.device
            gpt2_transformer = gpt2.transformer
            model_embeddings = gpt2_transformer.wte.weight
        elif gpt_model_name.startswith("facebook/opt-") or 'llama' in gpt_model_name:
            gpt2 = AutoModelForCausalLM.from_pretrained(gpt_model_name)
            gpt2 = deepspeed.init_inference(
                model=gpt2,
                dtype=torch.half,
                replace_method="auto", # Lets DS autmatically identify the layer to replace
                replace_with_kernel_inject=True, # replace the model with the kernel injector
                max_out_tokens=gpt2.config.max_position_embeddings, # max number of tokens to generate
            )
            gpt2.to(device)
            gpt2_transformer = gpt2.module.model
            if 'llama' in gpt_model_name:
                model_embeddings = gpt2_transformer.embed_tokens.weight
            else:
                model_embeddings = gpt2.module.model.decoder.embed_tokens.weight
        else:
            raise NotImplementedError()

        self.model = gpt2
        clip_model, _, preprocess = open_clip.create_model_and_transforms(*clip_model_name, device=self.vision_device)
        self.clip_preprocess = preprocess
        self.clip_model = clip_model.eval().requires_grad_(False).to(self.vision_device)
        self.filtered_words = self.get_vocab_mapping()
        prompts = ["a photo of a " + x for x in self.filtered_words.keys()]
        self.text_features = self.clip_model.encode_text(self.clip_tokenizer(prompts).to(self.vision_device)).float()
        self.text_features /= self.text_features.norm(dim=-1, keepdim=True)
        self.model_embeddings = model_embeddings
        self.table = model_embeddings.data.clone()
        if self.gpt_model_name == "EleutherAI/gpt-j-6B":
            self.table2_w = gpt2.lm_head.weight.data.clone()
            self.table2_b = gpt2.lm_head.bias.data.clone()

        self.modes = ['language']
        model_name = str(full_model_name).split("/")[-1]
        model_name = model_name.replace("-", "_")
        model_name = model_name.replace(".", "_")
        self.model_name = model_name

    # @lru_cache(maxsize=None)
    def get_vocab_mapping(self, use_filtered=False):
        # Get all of the tokens that map to words in text
        if use_filtered:
            text_vocab = filtered_words
        else:
            text_vocab = [self.tokenizer.decode([t_id]) for t_id in range(self.tokenizer.vocab_size)]
        # Re-encode pre-fixed with a space to avoid issues with the tokenizer
        full_vocab = [self.tokenizer.encode(" " + t, add_special_tokens=False)[:2][-1] for t in text_vocab]
        if not use_filtered:
            new_vocab = [i for i, t in enumerate(full_vocab) if i == t]
            # filter non-alphanumeric tokens
            new_vocab = [t for t in new_vocab if text_vocab[t].isalnum()]
            # filter out non-nouns
            new_vocab = [t for t in new_vocab if nlp(text_vocab[t])[0].pos_ == "NOUN"]
        else:
            new_vocab = full_vocab
        decoded_vocab = OrderedDict([(self.tokenizer.decode([t_id]), t_id) for t_id in new_vocab])
        return decoded_vocab

    def pre_eval_hook(self, df_metric, image_names):
        self.tok_map = self.encode_images(image_names)

    # @lru_cache(maxsize=None)
    def get_lookup(self, indices, values, ntags=10, reverse=False):
        # vocab = self.tokenizer.get_vocab()
        filtered_value_list = list(self.filtered_words.values())
        index = [filtered_value_list[i] for i in indices]
        if reverse:
            lookup_w = self.model.lm_head.weight.data[index].to(self.device)
            lookup_b = self.model.lm_head.bias.data[index].to(self.device)
        else:
            lookup = self.model_embeddings.data[index].to(self.device)
        weights = (10.0 * values[:ntags]).softmax(dim=-1).to(self.device)
        if reverse:
            lookup_w = (lookup_w[:ntags] * weights[:, None]).sum(0, keepdims=True)
            lookup_b = (lookup_b[:ntags] * weights[:, None]).sum(0, keepdims=True)
            lookup = (lookup_w, lookup_b)
        else:
            lookup = (lookup[:ntags] * weights[:, None]).sum(0, keepdims=True)
        return lookup

    def get_tags(self, image, topk=10):
        image = self.image_name_map[image]
        clip_vis_device = next(self.clip_model.visual.parameters()).device
        image = self.clip_preprocess(image).unsqueeze(0).to(clip_vis_device)
        image_features = self.clip_model.encode_image(image).cpu().float()
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        image_features = image_features.to(self.text_features.device)
        similarity = (100.0 * image_features @ self.text_features.T).softmax(dim=-1)
        values, indices = similarity[0].topk(topk)
        return indices, values

    def image_map(self, images, ntags=10, reverse=False):
        lookups = []
        for pic in images:
            indices, values = self.get_tags(pic, topk=ntags)
            lookup = self.get_lookup(indices, values, ntags=ntags, reverse=reverse)
            lookups.append(lookup)
        if reverse:
            lookups_w, lookups_b = zip(*lookups)
            lookups = (torch.vstack(lookups_w), torch.vstack(lookups_b))
        else:
            lookups = torch.vstack(lookups)
        return lookups

    def encode_images(self, imagevals, ntags=10):
        tokenizer = get_tokenizer(self.gpt_model_name)
        toks = [f'<img{x}>' for x in range(len(imagevals))]
        tokenizer._add_tokens(toks)
        lookups = self.image_map(imagevals, ntags=ntags)
        self.model_embeddings.data = torch.cat((self.table, lookups.to(self.table.device).type(self.table.type())), dim=0)
        if self.gpt_model_name == "EleutherAI/gpt-j-6B":
            (lookups_w, lookups_b) = self.image_map(imagevals, ntags=ntags, reverse=True)
            self.model.lm_head.weight.data = torch.cat((self.table2_w, lookups_w.to(self.table2_w.device).type(self.table2_w.type())), dim=0)
            self.model.lm_head.bias.data = torch.cat((self.table2_b, lookups_b.to(self.table2_b.device).type(self.table2_b.type()).sum(-1)), dim=0)

        tok_map = {image: tok for image, tok in zip(imagevals, toks)}
        self.tokenizer = tokenizer
        self.model.config.vocab_size = len(self.tokenizer)
        return tok_map

    # @lru_cache(maxsize=None)
    def get_score(self, image, text):
        text = self.tok_map[image] + "\n" + text
        lang_x = self.tokenizer(
            [text],
            return_tensors="pt",
        )
        lang_x = {k: v.to(self.device) for k, v in lang_x.items()}
        new_score = self.model(
            input_ids=lang_x["input_ids"],
            attention_mask=lang_x["attention_mask"],
            labels=lang_x["input_ids"],
        ).loss 
        new_score = new_score * (lang_x["input_ids"].shape[1] - 1)
        return new_score