"""avatarpipe -- AI human-avatar generation pipeline (PS02).

Package structure:
  spec.py              -- AvatarSpec schema and validation
  job_builder.py       -- spec -> portable job bundle (JSON)
  safety.py            -- pre-generation content policy checks
  inference_adapter.py -- adapter interface + LocalCPUStub + NotebookAdapter
  output_validator.py  -- post-generation image + manifest validation
  manifest.py          -- avatar_manifest.json writer/reader
  evaluation/          -- adherence, diversity, identity metrics
  consent.py           -- consent record + deletion controls (Exceptional tier)
  cli.py               -- avatarpipe CLI entrypoint
"""

__version__ = "0.1.0"
