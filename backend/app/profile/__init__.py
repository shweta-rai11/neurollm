"""Individual Computational Profile (ICP): the personalization layer that
sits between biometric identity (`app.biometric`) and the virtual-brain
pipeline (`app.brain`).

Two data paths are kept strictly separate here, per the product spec:

  Layer A -- Biometric identity: `app.biometric` answers "which profile does
  this fingerprint scan belong to?" via template similarity. That's all a
  fingerprint ever does in this app -- it is a lookup key, never an input to
  any trait-prediction formula.

  Layer B -- Learned computational profile: `learning.py` updates
  `ComputationalProfileParams` from *behavioral interaction data* (pathway
  chosen, hallucination risk, uncertainty agreement, explicit user
  feedback) -- never from fingerprint features. Every profile starts at
  neutral (0.5) defaults and only moves in response to observed behavior.
"""
