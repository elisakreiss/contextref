import open_clip
from evaluator import Evaluator
from functools import lru_cache

clip_models = open_clip.list_pretrained()

class CLIP_Evaluator(Evaluator):
    def initialize_model(self, model_name, use_base_model=True):
        model, _, preprocess = open_clip.create_model_and_transforms(*model_name, device=self.device)
        tokenizer = open_clip.get_tokenizer(model_name[0])
        self.model = model
        if use_base_model:
            base_model, _, preprocess = open_clip.create_model_and_transforms(*model_name, device=self.device)
            self.base_model = base_model
        self.preprocess = preprocess
        self.tokenizer = tokenizer
        self.modes = ['embed']

    # @lru_cache(maxsize=None)
    def embed_image(self, image_name):
        image = self.image_name_map[image_name]
        image = self.preprocess(image).unsqueeze(0).to(self.device)
        return self.model.encode_image(image)
    
    # @lru_cache(maxsize=None)
    def embed_text(self, text):
        text = self.tokenizer(text).to(self.device)
        return self.model.encode_text(text)