# Use of AI tools

The ideas, the analysis and the conclusions in this repository and in the accompanying deck are my own: the framing of the question, the choice of metrics and definitions, the reasoning, and the model behind the recommendation.

I verified the work myself, as a data analyst should, directly against on-chain data: the provided data, Dune Analytics, growthepie, the OP Mainnet block explorer (explorer.optimism.io) and other public sources. I checked that the queries are correct and that their output is correct.

AI tools helped me automate the work and move faster: coding the assignment, preparing tests for the output, and running other analysis and verification tasks. I also used them to improve the look of the slides.

How the output was checked: every figure shown is calculated in the notebooks and saved in one file, `output/numbers.json`, from which the slides were built. The tests in `tests/` reconcile the provided files with each other and with the external data, and the notebooks check that their key tables add up to the provided daily totals before using them.
