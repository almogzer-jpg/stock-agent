"""scanners/ — setup detectors.

Each scanner takes a metrics dict (from indicators/) and returns a boolean or
a tag. Add new scanners here (pullback, oversold-bounce, etc.) as the agent
grows. Currently: breakout.
"""
