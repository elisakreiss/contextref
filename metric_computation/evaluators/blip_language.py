from evaluator import Evaluator
from functools import lru_cache
from transformers import Blip2Processor, Blip2ForConditionalGeneration, AutoTokenizer
from lavis.models import load_model_and_preprocess

import torch

blip_language_models = [
    ("blip2_vicuna_instruct", "vicuna7b"),
    ("blip2_t5_instruct", 'flant5xxl'),
    # ("Salesforce/blip2-opt-2.7b-coco", None),
    # ("Salesforce/blip2-flan-t5-xl-coco", None),
    ("Salesforce/blip2-opt-6.7b", None),
    # ("Salesforce/blip2-flan-t5-xl", None),
    # ("Salesforce/blip2-opt-6.7b-coco", None),
    ("Salesforce/blip2-flan-t5-xxl", None)
    # ("Salesforce/blip2-opt-2.7b", None),
]

class BLIP_LanguageEvaluator(Evaluator):
    def initialize_model(self, full_model_name):
        full_model_name, model_type = full_model_name
        if "instruct" in full_model_name:
            self.model, image_processor, _ = load_model_and_preprocess(
                name=full_model_name, model_type=model_type, is_eval=True, device=self.device)
            self.tokenizer = AutoTokenizer.from_pretrained("Salesforce/blip2-opt-2.7b")
            image_processor_tmp = image_processor["eval"]
            self.image_processor = lambda images, return_tensors="pt": {"pixel_values": image_processor_tmp(images.convert('RGB'))}
            self.conditional_token = "<|cond|>"
            self.full_text_format = "{base_text}" + self.conditional_token + "{target_text}"
        else:
            self.model = Blip2ForConditionalGeneration.from_pretrained(
                full_model_name, torch_dtype=torch.float16).to(self.device)
            self.image_processor = Blip2Processor.from_pretrained(full_model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(full_model_name)
        self.modes = ['language']
        model_name = full_model_name.split("/")[-1]
        model_name = model_name.replace("-", "_")
        model_name = model_name.replace(".", "_")
        self.model_name = model_name

    # @lru_cache(maxsize=None)
    def get_score(self, image_name, text):
        image = self.image_name_map[image_name]
        image = self.image_processor(images=image, return_tensors="pt")
        image = image['pixel_values'].to(self.device, torch.float16)
        self.model.to(self.device)
        lang_x = self.tokenizer(
            [text],
            return_tensors="pt",
        )
        if "instruct" in self.model_name:
            text_output = text.split(self.conditional_token)[-1]
            text_input = text[:len(text) - len(text_output) - len(self.conditional_token)]
            data = {
                "image": image.unsqueeze(0),
                "text_input": text_input,
                "text_output": text_output,
            }
            new_score = self.model(data)['loss']
        else:
            lang_x = {k: v.to(self.device) for k, v in lang_x.items()}
            new_score = self.model(
                pixel_values=image,
                input_ids=lang_x["input_ids"],
                attention_mask=lang_x["attention_mask"],
                labels=lang_x["input_ids"],
            ).loss
        
        new_score = new_score * (lang_x["input_ids"].shape[1] - 1)
        return new_score