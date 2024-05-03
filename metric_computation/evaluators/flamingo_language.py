from evaluator import Evaluator
from functools import lru_cache
from open_flamingo import create_model_and_transforms
from huggingface_hub import hf_hub_download
import torch

flamingo_language_models = [
    ("openflamingo/OpenFlamingo-9B-vitl-mpt7b", "anas-awadalla/mpt-7b"),
    ("openflamingo/OpenFlamingo-9B", "decapoda-research/llama-7b-hf"),
]

class Flamingo_LanguageEvaluator(Evaluator):
    def initialize_model(self, model_name):
        model_name, model_type = model_name
        model, image_processor, tokenizer = create_model_and_transforms(
            clip_vision_encoder_path="ViT-L-14",
            clip_vision_encoder_pretrained="openai",
            lang_encoder_path=model_type,
            tokenizer_path=model_type,
            cross_attn_every_n_layers=4
        )

        checkpoint_path = hf_hub_download(
            model_name,
            "checkpoint.pt",
            token='HUGGINGFACETOKEN'
        )
        model.load_state_dict(torch.load(checkpoint_path), strict=False)
        model.lang_encoder.to(self.device)
        model.vision_encoder.to(self.device)

        self.model = model.to(torch.half)
        self.image_processor = image_processor
        self.tokenizer = tokenizer
        self.modes = ['language']
        full_model_name = model_name + "-" + model_type
        model_name = full_model_name.split("/")[-1]
        model_name = model_name.replace("-", "_")
        model_name = model_name.replace(".", "_")
        self.model_name = model_name

    # @lru_cache(maxsize=None)
    def get_score(self, image_name, text):
        image = self.image_name_map[image_name]
        image = self.image_processor(image).to(self.device, torch.float16)

        text = "<image>" + text
        lang_x = self.tokenizer(
            [text],
            return_tensors="pt",
        )
        lang_x = {k: v.to(self.device) for k, v in lang_x.items()}
        self.model.to(self.device)
        new_score = self.model(
            vision_x=image.unsqueeze(0).unsqueeze(0).unsqueeze(0),
            lang_x=lang_x["input_ids"],
            attention_mask=lang_x["attention_mask"],
            labels=lang_x["input_ids"],
        ).loss
        new_score = new_score * (lang_x["input_ids"].shape[1] - 1)
        return new_score