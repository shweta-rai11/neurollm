"""Real fingerprint image processing -> a numeric biometric template.

This package answers exactly one question: "what does this fingerprint
image look like, mathematically?" -- ridge orientation/frequency, minutiae,
singular points, pattern class, and image-quality metrics, all computed with
documented, standard fingerprint-recognition algorithms (Hong, Wan & Jain
1998 for orientation/frequency/Gabor enhancement; Zhang-Suen for
skeletonization; crossing-number for minutiae; Poincare index for
core/delta detection).

It does NOT answer "what does this fingerprint mean about the person" --
there is no function anywhere in this package (or in `app.profile`) that
maps a ridge/minutiae feature to a cognitive trait, brain region, or
neuromodulator value. The only thing that leaves this package is a
biometric identity template (`app.biometric.feature_vector.FeatureVector`)
consumed by `app.profile` purely as a lookup/personalization key -- see
`app.profile.service.ProfileService`.
"""
