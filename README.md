# OkunNLP: The First Parallel Corpus and Neural MT System for the Okun Language of Nigeria

This repository contains the dataset, code, and metadata for the NeurIPS 2026 Evaluations & Datasets Track paper *OkunNLP: The First Parallel Corpus and Neural MT System for the Okun Language of Nigeria*.

**Paper:** [link to OpenReview when available]
**Dataset:** <https://huggingface.co/datasets/Tobi-Shalom/english-Okun_corpus_Dataset>
**Author:** Oluwatobi Shalom Omotowa (Independent Researcher, Lagos, Nigeria)
**Contact:** oluwatobishalom2002@gmail.com

## Overview

OkunNLP is the first English–Okun parallel corpus, comprising **5,015 verse-aligned sentence pairs** extracted from six books of the Okun Bible (Bible Society of Nigeria, 2022) and aligned with the public-domain King James Version. Okun is a Northeast Yoruba dialect cluster spoken by over two million people in Kogi State, Nigeria, and is currently absent from every major multilingual NLP benchmark.

This repository contains the full pipeline used to construct the corpus and to fine-tune baseline NMT models, plus the Croissant 1.0 metadata file (with Responsible AI fields) required for NeurIPS submission.

## Repository Structure

```
.
├── README.md                       This file
├── LICENSE                         CC-BY-NC-4.0 (dataset)
├── LICENSE-CODE                    MIT (code)
├── requirements.txt                Python dependencies
├── okunnlp_croissant.json          Dataset metadata (Croissant 1.0 + RAI)
├── DATASHEET.md                    Datasheet for the corpus
│
├── notebooks/
│   ├── 01_pdf_page_extraction.ipynb     Render PDF pages and split two-page spreads
│   ├── 02_ocr_data_collection.ipynb     OCR via Google Cloud Vision API
│   ├── 03_verse_extraction.ipynb        Parse OCR output into structured verses
│   ├── 04_corpus_cleaning.ipynb         Clean, align, and quality-filter verse pairs
│   └── 05_model_finetuning.ipynb        Fine-tune NLLB-200 / M2M100 baselines
│
└── src/
    └── enhanced_okun_extractor.py       Standalone extractor utilities
```

## Installation

Tested with **Python 3.10+** on Linux and Google Colab (T4 / A100 GPU).

```bash
git clone https://github.com/Shallyquinn/Okun-digitization.git
cd Okun-digitization
pip install -r requirements.txt
```

For the OCR step you will additionally need:

- A Google Cloud Vision API key (export `GOOGLE_APPLICATION_CREDENTIALS` to point to your service-account JSON), and
- `poppler-utils` installed system-wide (required by `pdf2image`).

```bash
# Ubuntu / Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler
```

For the fine-tuning step a CUDA-capable GPU with at least 16 GB VRAM is recommended.

## Reproducing the Pipeline

The notebooks are numbered in the order they should be run. Each notebook reads from the output of the previous one.

| Step | Notebook | Input | Output |
|---|---|---|---|
| 1 | `01_pdf_page_extraction.ipynb` | Scanned Okun Bible PDF | Per-page PNG images at 300 DPI, split at column midpoint |
| 2 | `02_ocr_data_collection.ipynb` | Page images | Raw OCR JSON (text + confidence per region) |
| 3 | `03_verse_extraction.ipynb` | Raw OCR JSON | Structured verses keyed by `Book Chapter:Verse` |
| 4 | `04_corpus_cleaning.ipynb` | Structured verses | `okun_corpus_final.csv` with train/dev/test split |
| 5 | `05_model_finetuning.ipynb` | `okun_corpus_final.csv` | Fine-tuned model checkpoint and BLEU/chrF scores |

The released corpus (5,015 pairs) and the quality-filtered experimental subset (1,959 pairs, 80/10/10 split with OCR confidence > 0.85) are both produced by step 4.

## Dataset

The corpus is hosted on Hugging Face: <https://huggingface.co/datasets/Tobi-Shalom/english-Okun_corpus_Dataset>

Quick stats:

- **Languages:** English (`en`) ↔ Okun (`okun`)
- **Pairs:** 5,015 total · 1,959 quality-filtered (train 1,567 / dev 196 / test 196)
- **Source books:** Psalms, Job, Proverbs, Ecclesiastes, Song of Solomon, Isaiah 1–10
- **Format:** UTF-8 CSV with columns `Reference`, `English (KJV)`, `Okun`, `OCR_Confidence`, `Split`

See `DATASHEET.md` and `okunnlp_croissant.json` for full documentation, including Responsible AI metadata (collection method, biases, limitations, intended use, out-of-scope use, and social impact).

## Citation

```bibtex
@inproceedings{omotowa2026okunnlp,
  title={OkunNLP: The First Parallel Corpus and Neural MT System for the Okun Language of Nigeria},
  author={Omotowa, Oluwatobi Shalom},
  booktitle={Proceedings of the 40th Conference on Neural Information Processing Systems (NeurIPS 2026) Evaluations and Datasets Track},
  year={2026},
  address={Sydney, Australia}
}
```

## License

- **Code** (notebooks and `src/`): MIT — see `LICENSE-CODE`.
- **Dataset** (corpus, Croissant metadata): CC-BY-NC-4.0 — see `LICENSE`.

The underlying Okun Bible text is © Bible Society of Nigeria (2022). The corpus is released for non-commercial research and educational use only; redistribution of the underlying translation requires permission from the Bible Society of Nigeria. The English column uses the King James Version (1611), which is in the public domain.

## Acknowledgements

Thanks to the native Okun speakers (Ijumu dialect) who conducted the manual quality review, and to the Bible Society of Nigeria for producing the Okun Holy Bible (2022) that made this work possible.
