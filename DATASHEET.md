# Datasheet for OkunNLP

Following Gebru et al., *Datasheets for Datasets* (2021).

**Author:** Oluwatobi Shalom Omotowa (Independent Researcher, Lagos, Nigeria)
**Contact:** oluwatobishalom2002@gmail.com
**Dataset:** <https://huggingface.co/datasets/Tobi-Shalom/english-Okun_corpus_Dataset>

## Motivation

**For what purpose was the dataset created?**
To enable neural machine translation research for Okun, a Northeast Yoruba dialect cluster spoken by over two million people in Kogi State, Nigeria. Prior to this work, no parallel corpus existed for Okun, and the language is unsupported by every major MT system. The dataset is intended to (a) provide a first benchmark for Okun MT, (b) serve as a starting resource for transfer-learning studies on closely related Yoruba dialects, and (c) support broader low-resource NLP research on under-served African languages.

**Who created the dataset?**
Oluwatobi Shalom Omotowa, Independent Researcher, Lagos, Nigeria. Native Okun speakers of the Ijumu dialect contributed manual quality verification on a sample of 100 pairs.

**Who funded the creation?**
Self-funded.

## Composition

**What do the instances represent?**
Each instance is a verse-aligned English–Okun sentence pair. The English column is from the King James Version (1611, public domain). The Okun column is from the Okun Holy Bible (Bible Society of Nigeria, 2022).

**How many instances are there?**
The release contains two files:

- `okun_corpus_full_5015.csv` — the complete 5,015-pair corpus (Reference, English (KJV), Okun).
- `okun_corpus_experimental_1959.csv` — the 1,959-pair subset used for MT experiments, including a `Split` column with train/dev/test labels (1,567 / 196 / 196).

**Why two files?**
The 1,959-pair subset was the data ready and verified at the time the MT experiments were run; the full 5,015-pair corpus was completed subsequently. Releasing both preserves the exact reproducibility of the paper's BLEU figures while also providing the broader corpus for downstream research.

**Source books:** Psalms, Job, Proverbs, Ecclesiastes, Song of Solomon, and Isaiah 1–10.

**Does the dataset contain all possible instances or is it a sample?**
Sample. The Okun Bible contains the complete Old and New Testaments. This corpus covers six Old Testament books selected for prioritising poetic and wisdom literature.

**What data does each instance consist of?**
Three or four fields depending on file: `Reference` (e.g., `Psalms 1:1`), `English (KJV)`, `Okun`, and (experimental file only) `Split` (`train` / `dev` / `test`).

**Is there a label or target field?**
For MT training, `English (KJV)` is the source and `Okun` is the target. The task is symmetric and can be flipped.

**Is any information missing?**
Verses where OCR failed to extract usable text are marked `[MISSING]`. Manual review on 100 sampled pairs identified roughly 17% with at least one diacritic-related OCR error.

**Are relationships between instances made explicit?**
Yes. The `Reference` field gives canonical biblical addressing, allowing chapter- and book-level grouping.

**Recommended data splits?**
The `Split` column on the experimental file gives the exact train/dev/test partition used to produce the BLEU figures in the paper. Use this for reproducing the baselines.

**Errors, sources of noise?**
OCR errors, especially in Psalms 100–150 where spine curvature caused approximately 38% diacritic omission at the page level. Possible Yoruba lexical bleed inherited from the Yoruba Common Language Bible source text.

**Self-contained, or does it rely on external resources?**
Self-contained. No external links or APIs are required to use the corpus.

**Does the dataset contain confidential, offensive, or sensitive material?**
No personal data. No PII. No offensive content beyond what is present in the canonical biblical text itself (e.g., violent imagery in Psalms imprecations).

## Collection Process

**How was the data acquired?**
Smartphone photography of the printed Okun Bible, followed by PDF rendering at 300 DPI, two-page-spread splitting, image enhancement (contrast ×1.3, sharpness ×1.5), and OCR via Google Cloud Vision API. Verses were aligned using deterministic chapter-verse counters from the canonical biblical structure.

**Who was involved?**
Data collection and pipeline development by the author. Manual quality review on 100 randomly sampled pairs was conducted by native Okun speakers of the Ijumu dialect.

**Over what timeframe was the data collected?**
October 2024 – April 2026.

**Were ethical review processes conducted?**
The data is biblical text and contains no human-subjects information. No IRB review was required. Permission considerations relating to the Bible Society of Nigeria copyright are addressed under "Distribution" below.

## Preprocessing / Cleaning / Labeling

**Was any preprocessing or cleaning done?**
Yes. Pages were rasterised, rotated, and split. Images were enhanced before OCR. OCR output was parsed into chapter-verse structures, and verse alignment was performed deterministically. The 1,959-pair experimental subset was selected by manual verification of cleanliness — full diacritical preservation and unambiguous verse alignment — during the early phase of corpus construction.

**Is the raw data also available?**
The page images and raw OCR JSON are not redistributed (to limit redistribution of the underlying copyrighted Okun text), but the pipeline notebooks allow reconstruction from a user's own copy of the Okun Bible PDF.

## Uses

**Has the dataset been used for any tasks already?**
Yes — fine-tuning NLLB-200 and M2M100 for English↔Okun translation. Results are reported in the accompanying paper.

**Is there a repository linking publications using the dataset?**
The accompanying paper and code: <https://github.com/Shallyquinn/Okun-digitization>.

**What other tasks could the dataset be used for?**
Cross-dialect transfer (Yoruba ↔ Okun), corpus linguistics on Okun morphology and tone, low-resource MT methodology research, and educational tooling for Okun-language preservation.

**Is there anything that could result in unfair treatment or harm?**
The biblical-domain bias means models trained only on this corpus will translate religious register well but perform poorly on conversational, technical, or modern usage. Out-of-domain BLEU drops by 48–49 points. Users should not deploy models trained only on this corpus for medical, legal, or safety-critical translation.

**Are there tasks for which the dataset should not be used?**
Commercial deployment (license is CC-BY-NC-4.0). Real-time production translation without further domain adaptation. Modelling of Southwest or Southeast Yoruba dialects, which differ substantially from the Okun cluster.

## Distribution

**Will the dataset be distributed?**
Yes, on Hugging Face: <https://huggingface.co/datasets/Tobi-Shalom/english-Okun_corpus_Dataset>.

**Under what license?**
CC-BY-NC-4.0. The underlying Okun translation remains © Bible Society of Nigeria (2022). Formal permission for academic, non-commercial research use has been requested from the Bible Society of Nigeria. The English KJV column is public domain.

**Are there third-party IP-based or other restrictions?**
Yes. The Okun text is © Bible Society of Nigeria (2022). The CC-BY-NC-4.0 license applies to the dataset compilation, alignment, and metadata; users must independently respect BSN's copyright in the underlying translation.

**Do any export controls or regulatory restrictions apply?**
None known.

## Maintenance

**Who will support / host / maintain the dataset?**
The author (contact above) on Hugging Face Hub.

**How can the curator be contacted?**
oluwatobishalom2002@gmail.com.

**Will the dataset be updated?**
Yes. Future versions will (a) extend coverage to the remaining Okun Bible books, (b) include the New Testament, and (c) add automated diacritic-correction passes. Versioned releases will be tagged on the Hugging Face dataset.

**Will older versions continue to be supported?**
All versions will remain available via Hugging Face's revision history.

**If others want to extend / build on the dataset, is there a mechanism?**
Yes — issues and pull requests on the GitHub repository: <https://github.com/Shallyquinn/Okun-digitization>.
