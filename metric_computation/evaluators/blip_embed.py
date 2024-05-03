from lavis.models.blip_models.blip_outputs import BlipOutput, BlipOutputFeatures
from lavis.models import load_model_and_preprocess
from functools import lru_cache
from evaluator import Evaluator
import torch

def extract_features(self, samples, mode="multimodal"):
        """
        Extract features for multimodal or unimodal samples.
        Args:
            samples (dict): A dictionary of samples, containing the following keys:
                - image (torch.Tensor): A tensor of shape (B, C, H, W) containing the image.
                    Raw images should be preprocessed before being passed to feature extractor.
                - text_input (list): A list of strings containing the text, length B.
            mode (str): The mode of feature extraction. Can be either "multimodal", "text" or "image".
                If "multimodal", return image features and multimodal features;
                if "text", return text features;
                if "image", return image features.
                Default: "multimodal".
        Returns:
            BlipOutputFeatures: A BlipOutputFeatures object containing the features.
                See lavis/models/blip_models/blip_outputs.py for more details.
        """
        image = samples.get("image")
        caption = samples.get("text_input")

        # assert mode is one of "image", "text", "multimodal"
        assert mode in [
            "image",
            "text",
            "multimodal",
        ], "mode must be one of 'image', 'text', 'multimodal'"

        # initalize output
        image_embeds, text_embeds, multimodal_embeds = None, None, None
        image_features, text_features = None, None

        if mode == "image":
            assert (
                image is not None
            ), "Image is not provided for mode 'image' or 'multimodal'"
            # return query features
            with self.maybe_autocast():
                image_embeds_frozen = self.ln_vision(self.visual_encoder(image))
            image_embeds_frozen = image_embeds_frozen.float()
            image_atts = torch.ones(
                image_embeds_frozen.size()[:-1], dtype=torch.long
            ).to(self.device)
            query_tokens = self.query_tokens.expand(
                image_embeds_frozen.shape[0], -1, -1
            )

            query_output = self.Qformer.bert(
                query_embeds=query_tokens,
                encoder_hidden_states=image_embeds_frozen,
                encoder_attention_mask=image_atts,
                return_dict=True,
            )
            image_embeds = query_output.last_hidden_state
            image_features = self.vision_proj(image_embeds)

        elif mode == "text":
            assert (
                caption is not None
            ), "text input is None for mode 'text' or 'multimodal'"

            # return text features
            text = self.tokenizer(caption, return_tensors="pt", padding=True).to(
                self.device
            )

            text_output = self.Qformer.bert(
                text.input_ids,
                attention_mask=text.attention_mask,
                return_dict=True,
            )
            text_embeds = text_output.last_hidden_state
            text_features = self.text_proj(text_embeds)
        return BlipOutputFeatures(
            image_embeds=image_embeds,
            image_embeds_proj=image_features,
            text_embeds=text_embeds,
            text_embeds_proj=text_features,
            multimodal_embeds=multimodal_embeds,
        )

def itc_image(self, image, device):
    with self.maybe_autocast():
        image_embeds = self.ln_vision(self.visual_encoder(image))
    image_embeds = image_embeds.float()
    image_atts = torch.ones(image_embeds.size()[:-1], dtype=torch.long).to(
        device
    )

    query_tokens = self.query_tokens.expand(image_embeds.shape[0], -1, -1)

    query_output = self.Qformer.bert(
        query_embeds=query_tokens,
        encoder_hidden_states=image_embeds,
        encoder_attention_mask=image_atts,
        return_dict=True,
    )
    image_feats = self.vision_proj(query_output.last_hidden_state)
    return image_feats

def itc_text(self, caption, device):
    text = self.tokenizer(
        caption,
        truncation=True,
        max_length=self.max_txt_len,
        return_tensors="pt",
    ).to(device)

    text_output = self.Qformer.bert(
        text.input_ids,
        attention_mask=text.attention_mask,
        return_dict=True,
    )
    text_feat = self.text_proj(text_output.last_hidden_state[:, 0, :])
    return text_feat

blip_embed_models = [
    ("blip2_image_text_matching", 'pretrain_vitL'),
    ("blip2_feature_extractor", 'pretrain_vitL'),
    ("blip2_image_text_matching", 'pretrain'),
    ("blip2_feature_extractor", 'pretrain'),
]

class BLIP_EmbedEvaluator(Evaluator):
    def initialize_model(self, model_name):
        model_name, model_type = model_name
        model, vis_processors, txt_processors = load_model_and_preprocess(
            name=model_name, model_type=model_type, is_eval=True, device=self.device
        )
        self.model = model
        self.model_name = model_name
        self.vis_processors = vis_processors["eval"]
        self.txt_processors = txt_processors["eval"]
        self.modes = ['embed']

    # @lru_cache(maxsize=None)
    def embed_image_feature(self, image_name):
        image = self.image_name_map[image_name]
        image = self.vis_processors(image).unsqueeze(0).to(self.device)
        sample = {"image": image}
        features = extract_features(self.model, sample, mode="image").image_embeds_proj[:, 0, :]
        return features

    # @lru_cache(maxsize=None)
    def embed_image_contrastive(self, image_name):
        image = self.image_name_map[image_name]
        image = self.vis_processors(image).unsqueeze(0).to(self.device)
        features = itc_image(self.model, image, self.device)
        assert features.shape[0] == 1, "Batch size must be 1"
        features = features.squeeze(0)
        return features

    def embed_image(self, image_name):
        if self.model_name == "blip2_feature_extractor":
            return self.embed_image_feature(image_name)
        if self.model_name == "blip2_image_text_matching":
            return self.embed_image_contrastive(image_name)
    
    def embed_text(self, text):
        if self.model_name == "blip2_feature_extractor":
            sample = {"text_input": [text]}
            features = extract_features(self.model, sample, mode="text").text_embeds_proj[:, 0, :]
            return features
        if self.model_name == "blip2_image_text_matching":
            features = itc_text(self.model, text, self.device)
            return features