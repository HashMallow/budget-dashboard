# Voice feedback (tracked docs)

**Git-tracked** English summaries from product-owner voice notes.  
Persian transcripts and raw audio stay local under `.artifacts/` (gitignored).

| File | Purpose |
|------|---------|
| **[`PROCESSING_LOG.en.md`](PROCESSING_LOG.en.md)** | Transcription verification, requests, fixes shipped, backlog — **update this after each batch** |
| [`USER_REQUESTS.en.md`](USER_REQUESTS.en.md) | Main topics the product owner asked for |

Local-only (not in git):

- `.artifacts/audio/` · `.artifacts/voice-feedback/audio/` — source `.ogg`
- `.artifacts/voice-feedback/transcripts/` — Persian `*_transcript.fa.md`
- `.artifacts/voice-feedback/batch_transcribe.log` — batch run output

Transcription: conda `ml-env`, `tools/batch_transcribe_artifacts.py`.
