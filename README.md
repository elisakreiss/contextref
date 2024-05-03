# ContextRef: Evaluating Referenceless Metrics For Image Description Generation

This repository hosts all code and data for the paper **ContextRef: Evaluating Referenceless Metrics For Image Description Generation** (ICLR, 2024).

## Repository guide

This repository contains all code necessary for running the metric evaluation (`metric_computation`), analyze the metrics (`metric_analysis`), replicate the human subject experiment (`dataset/human_subject_study`), and analyze the human subject study results (`dataset/human_subject_analysis`).

### Adding necessary data folders

In order to execute the `metric_analysis` codes and for replicating the full dataset pipeline, you will need to additionally download two data repositories. Firstly, you can download the [data](https://drive.google.com/drive/folders/1l_7jfsXZX99ZEGO0fIuaSbxorDmB4Gpc?usp=sharing) folder which includes all data augmentations used and sampled annotated data, and place it within the `datasets` folder.

The complete model metric outputs can be downloaded [here](https://drive.google.com/drive/folders/1lHFHyy_JFiEH1tchwsFTOEvQu-Yk9MqU?usp=sharing). This `metric_outputs` folder needs to be inserted in the main directory of this repository.

## Citation

If you find this repo or the paper useful in your research, please feel free to cite [our paper](https://arxiv.org/abs/2309.11710):

```
@inproceedings{
  kreiss2024contextref,
  title={ContextRef: Evaluating Referenceless Metrics for Image Description Generation},
  author={Elisa Kreiss and Eric Zelikman and Christopher Potts and Nick Haber},
  booktitle={The Twelfth International Conference on Learning Representations},
  year={2024},
  url={https://openreview.net/forum?id=j0ZvKSNZiP}
}
```
