# generate_docs.py — Create mock market research documents
# Run once to populate the documents/ folder

import os

DOCS_DIR = "documents"
os.makedirs(DOCS_DIR, exist_ok=True)

documents = {
    "btc_crash_2022.md": """# Bitcoin Bear Market Analysis — 2022

## Summary
Bitcoin experienced a severe decline throughout 2022, falling from approximately $47,000 in January to a low of $15,500 in November. The decline was driven by multiple factors including the Federal Reserve's aggressive rate hiking cycle, the collapse of the Terra/Luna ecosystem in May, and the FTX bankruptcy in November.

## Key Events
The Terra/Luna collapse in May 2022 wiped out approximately $40 billion in value and triggered a cascade of liquidations across the crypto ecosystem. Three Arrows Capital, a major crypto hedge fund, became insolvent shortly after, owing creditors over $3 billion.

The FTX collapse in November 2022 was the final major shock. FTX, previously the third-largest cryptocurrency exchange, filed for bankruptcy after it was revealed that customer funds had been misappropriated. Bitcoin fell from $21,000 to $15,500 in the aftermath.

## Technical Analysis
Bitcoin broke below its 200-week moving average for only the fourth time in history during the 2022 bear market. The RSI on the weekly chart reached oversold levels not seen since March 2020. On-chain metrics showed long-term holders accumulating aggressively below $20,000, a historically reliable bottom signal.

## Macro Context
The Federal Reserve raised interest rates from near zero to 4.25-4.50% during 2022, the most aggressive tightening cycle in decades. This created significant headwinds for risk assets broadly, with the S&P 500 falling 19% and the Nasdaq declining 33% over the same period.
""",

    "eth_merge_2022.md": """# Ethereum Merge Analysis — September 2022

## Summary
Ethereum completed its transition from Proof of Work to Proof of Stake on September 15, 2022, in an event known as "The Merge." This was the most significant technical upgrade in cryptocurrency history, reducing Ethereum's energy consumption by approximately 99.95%.

## Price Action
Despite the technical success, ETH price declined from approximately $1,700 before the Merge to $1,300 by the end of September. The "buy the rumour, sell the news" dynamic was evident, as ETH had rallied from $900 in June anticipating the upgrade.

## Impact on Supply
The Merge introduced a deflationary mechanism. Under Proof of Work, approximately 13,000 ETH were issued daily. Under Proof of Stake, issuance dropped to roughly 1,700 ETH per day. Combined with EIP-1559's fee burning mechanism, Ethereum became net deflationary during periods of high network activity.

## Staking Economics
Post-Merge, ETH staking yields settled around 4-5% APR. This created a new dynamic where ETH became a yield-bearing asset, competing with traditional fixed-income instruments. By the end of 2022, approximately 15 million ETH (12% of supply) was staked.

## Risks Identified
Centralisation concerns emerged as Lido Finance controlled over 30% of staked ETH. Client diversity was also flagged, with Prysm running on over 60% of validators. Both represented single points of failure for the network.
""",

    "fed_rates_2023.md": """# Federal Reserve Rate Policy — 2023 Review

## Summary
The Federal Reserve continued its rate hiking cycle into 2023, raising the federal funds rate from 4.25-4.50% to 5.25-5.50% by July. The pace of hikes slowed significantly compared to 2022, with three 25bp increases before pausing.

## Banking Crisis
In March 2023, Silicon Valley Bank (SVB) collapsed after a bank run triggered by unrealised losses on its bond portfolio. Signature Bank and First Republic Bank also failed. The Fed responded with the Bank Term Funding Program (BTFP), providing emergency liquidity to prevent contagion.

## Impact on Markets
Despite the banking turmoil, equity markets rallied through 2023. The S&P 500 gained approximately 24%, driven largely by the "Magnificent Seven" tech stocks. Bitcoin recovered to $42,000 by year end, benefiting from a narrative shift toward Bitcoin as a hedge against banking system fragility.

## Inflation Trajectory
Core PCE inflation fell from 4.9% in January to 2.9% by December 2023. The disinflation trend supported expectations for rate cuts in 2024, though the Fed maintained a "higher for longer" stance through most of the year.

## Bond Market
The 10-year Treasury yield reached 5% in October 2023, the highest since 2007. The yield curve remained inverted for the longest continuous period in history, though the predicted recession had not materialised by year end.
""",

    "nvidia_ai_boom.md": """# NVIDIA and the AI Investment Boom — 2023-2024

## Summary
NVIDIA emerged as the primary beneficiary of the artificial intelligence investment wave following the launch of ChatGPT in November 2022. The company's data centre revenue grew from $3.6 billion in Q1 FY2023 to $18.4 billion in Q3 FY2024, driven by insatiable demand for GPU computing.

## Competitive Position
NVIDIA's H100 GPU became the must-have chip for AI training and inference. The company maintained over 80% market share in AI accelerators. AMD's MI300X represented the strongest competitive threat, while cloud providers including Google (TPUs), Amazon (Trainium), and Microsoft developed custom silicon.

## Valuation Concerns
NVIDIA's market capitalisation exceeded $1.2 trillion by the end of 2023, representing a forward P/E ratio above 30x. Bulls argued this was justified by the total addressable market for AI infrastructure, estimated at $150-300 billion annually by 2027. Bears pointed to cyclical risk in semiconductor demand and potential for customers to develop alternatives.

## Supply Chain
TSMC's advanced packaging capacity (CoWoS) was the primary bottleneck for H100 production. Lead times exceeded 50 weeks through most of 2023. NVIDIA secured priority allocation through large upfront commitments, further entrenching its position.

## Broader AI Trade
The AI investment theme extended beyond NVIDIA. Companies across the semiconductor supply chain benefited, including ASML, Applied Materials, and Broadcom. Cloud infrastructure spending by Microsoft, Google, Amazon, and Meta reached record levels, with each committing $30-50 billion in annual capital expenditure for AI infrastructure.
""",

    "gold_2023.md": """# Gold Market Analysis — 2023

## Summary
Gold reached a new all-time high of $2,135 per ounce in December 2023, breaking the previous record set in August 2020. The rally was driven by central bank purchases, geopolitical tensions, and expectations for Federal Reserve rate cuts.

## Central Bank Buying
Central banks purchased over 1,000 tonnes of gold in 2023, the second consecutive year of record buying. China's PBOC was the largest buyer, adding 225 tonnes to reserves. The trend reflected a broader shift away from US dollar reserves, particularly among emerging market central banks.

## Geopolitical Premium
The Israel-Hamas conflict beginning in October 2023 added a geopolitical risk premium to gold. The metal rallied approximately $200 from October through December. Historical analysis shows gold typically maintains geopolitical premiums for 2-6 months before mean-reverting.

## Real Rates Relationship
Gold's rally occurred despite real interest rates (10-year TIPS yield) remaining above 2%, historically a headwind for gold. This divergence from the traditional inverse correlation suggested structural demand factors (central bank buying, de-dollarisation) were overriding rate sensitivity.

## Technical Outlook
The breakout above the $2,075 resistance level that had capped gold since 2020 was technically significant. The measured move from the multi-year base pattern projected a target of $2,400-2,500. Support was established at $2,000-2,050.
""",

    "sp500_2024_q1.md": """# S&P 500 Q1 2024 Review

## Summary
The S&P 500 gained 10.2% in Q1 2024, marking one of the strongest first quarters in decades. The rally was broad-based compared to 2023, with the equal-weighted index outperforming the cap-weighted index for the first time in five quarters.

## Sector Performance
Technology led gains at +12.7%, followed by Communication Services (+11.8%) and Industrials (+10.1%). Utilities were the weakest sector at +3.2%, weighed down by rising bond yields. Healthcare underperformed at +5.1% due to uncertainty around GLP-1 drug pricing.

## Earnings Season
Q4 2023 earnings (reported in Q1 2024) showed a return to growth after three quarters of decline. S&P 500 earnings grew 4.0% year-over-year, with the Technology sector leading at +23%. Revenue growth was modest at 3.7%, indicating margin expansion was the primary driver.

## Federal Reserve
Markets entered 2024 pricing six rate cuts for the year. By March, expectations had moderated to three cuts, beginning in June. The repricing caused temporary volatility in January but markets ultimately rallied on strong economic data, embracing a "no landing" scenario over recession fears.

## Concentration Risk
Despite improved breadth, the top 10 stocks still represented 34% of S&P 500 market capitalisation. NVIDIA alone contributed approximately 2% of the index's Q1 return. The market's dependence on a handful of mega-cap tech stocks remained a structural vulnerability.
""",

    "btc_etf_2024.md": """# Bitcoin ETF Approval and Market Impact — January 2024

## Summary
The SEC approved 11 spot Bitcoin ETFs on January 10, 2024, ending a decade-long battle for a regulated Bitcoin investment vehicle in the US. The approval was a watershed moment for cryptocurrency institutional adoption.

## Flow Data
In the first three months of trading, spot Bitcoin ETFs attracted over $12 billion in net inflows. BlackRock's iShares Bitcoin Trust (IBIT) led with $17.6 billion in gross inflows, making it the most successful ETF launch in history by AUM accumulation. Grayscale's GBTC experienced $14.7 billion in outflows as investors rotated from the higher-fee trust to new ETF options.

## Price Impact
Bitcoin rallied from $44,000 at the time of approval to a new all-time high of $73,000 in March 2024. The "sell the news" dip was shallow and brief, lasting only two weeks. Daily ETF buying absorbed an estimated 10x the daily Bitcoin mining supply, creating persistent upward pressure.

## Market Structure Changes
The ETF approval fundamentally changed Bitcoin's market structure. Trading volumes shifted from crypto-native exchanges toward regulated venues. Basis trading (buying spot ETF, selling CME futures) became a popular institutional strategy, with annualised yields of 15-20%.

## Regulatory Implications
The approval opened the door for broader crypto ETF products. Ethereum ETF applications from BlackRock and Fidelity were filed within weeks. The precedent also strengthened the case for cryptocurrency as a legitimate asset class in institutional portfolio construction.
""",

    "oil_geopolitics_2024.md": """# Oil Market and Geopolitical Risk — 2024

## Summary
Crude oil prices traded in a $70-85 range through early 2024, caught between geopolitical risk premiums and weak demand signals from China. Brent crude averaged $82 per barrel in Q1, roughly flat year-over-year.

## Middle East Tensions
Houthi attacks on Red Sea shipping beginning in December 2023 disrupted approximately 12% of global trade. Shipping costs on the Asia-Europe route increased 300%. However, the impact on oil supply was limited as alternative routes around the Cape of Good Hope were available, adding 10-14 days to transit times.

## OPEC+ Dynamics
Saudi Arabia extended voluntary production cuts of 1 million barrels per day through Q1 2024. OPEC+ compliance with agreed cuts was mixed, with Iraq and UAE consistently exceeding quotas. Russia's production remained difficult to verify independently following sanctions.

## China Demand
Chinese oil demand growth slowed to approximately 400,000 barrels per day year-over-year in Q1 2024, down from over 1 million barrels per day in 2023. The property sector downturn and slower economic growth weighed on diesel and petrochemical demand. Electric vehicle penetration in China exceeded 35% of new car sales, structurally reducing gasoline demand growth.

## US Production
US crude oil production reached a record 13.3 million barrels per day in early 2024. Shale producers maintained discipline, prioritising free cash flow and shareholder returns over volume growth. The Permian Basin alone produced over 6 million barrels per day.
""",

    "japan_rates_2024.md": """# Bank of Japan Rate Decision — March 2024

## Summary
The Bank of Japan ended its negative interest rate policy on March 19, 2024, raising the overnight rate from -0.1% to 0-0.1%. This was the first rate increase in 17 years and marked the end of the world's last negative rate regime.

## Background
Japan maintained negative rates since January 2016 and yield curve control since September 2016. Core CPI inflation exceeded the BOJ's 2% target for 18 consecutive months, and the spring wage negotiations (shunto) delivered the largest pay increases in 33 years at 5.28%.

## Market Reaction
The Japanese yen initially weakened following the decision, counterintuitively, as the BOJ signalled a very gradual normalisation path. USD/JPY rose from 149 to 151 in the week following the decision. The Nikkei 225 rallied to a new all-time high above 40,000, surpassing its 1989 bubble-era peak.

## Carry Trade Implications
The yen carry trade — borrowing in cheap yen to invest in higher-yielding assets — had accumulated to an estimated $500 billion. The gradual pace of BOJ tightening meant the carry trade was not immediately threatened, but any acceleration in rate hikes posed a risk of disorderly unwinding.

## Global Impact
Japan's rate normalisation had implications for global bond markets. Japanese institutions were the largest foreign holders of US Treasuries ($1.1 trillion). Higher domestic yields could encourage repatriation of capital, putting upward pressure on US yields.
""",

    "crypto_defi_risks.md": """# DeFi Risk Assessment — Ongoing Concerns

## Summary
Decentralised finance protocols continue to present significant risks despite technological improvements. Smart contract vulnerabilities, governance attacks, and regulatory uncertainty remain primary concerns for institutional adoption.

## Smart Contract Risk
In 2023 alone, DeFi protocols lost over $1.7 billion to hacks and exploits. Major incidents included the Euler Finance hack ($197 million) and the Curve Finance pool exploit ($70 million). Audit firms including Trail of Bits and OpenZeppelin have noted that the complexity of DeFi protocols has outpaced the ability of auditing to provide comprehensive security guarantees.

## Governance Risks
Token-based governance systems have proven vulnerable to vote buying, flash loan governance attacks, and plutocratic concentration. In several major protocols, fewer than 10 wallets control over 50% of governance tokens. This creates the risk of protocol changes that benefit large holders at the expense of users.

## Stablecoin Risks
Following the Terra/UST collapse, algorithmic stablecoins remain high-risk. USDT (Tether) maintains its peg but questions about reserve quality persist. USDC (Circle) has emerged as the institutional preference due to greater transparency, though its brief depeg during the SVB crisis in March 2023 highlighted systemic banking dependencies.

## Regulatory Outlook
The SEC's enforcement-first approach has created uncertainty for DeFi participants. The classification of governance tokens as securities would fundamentally alter the DeFi landscape. European MiCA regulation provides a clearer framework but may exclude truly decentralised protocols.

## Institutional View
Most institutional investors treat DeFi as uninvestable under current risk frameworks. The exceptions are large stablecoin allocations (USDC) and structured products offered through regulated intermediaries. Direct DeFi protocol exposure remains limited to crypto-native funds.
""",

    "tsx_energy_2024.md": """# Canadian Energy Sector — TSX Analysis 2024

## Summary
The Canadian energy sector on the TSX showed mixed performance in early 2024. Integrated producers benefited from stable oil prices while natural gas-weighted companies suffered from record-low North American gas prices, with AECO hub prices falling below $2/GJ.

## Trans Mountain Pipeline
The completion of the Trans Mountain Expansion (TMX) pipeline in May 2024 was a game-changer for Canadian heavy oil producers. The additional 590,000 barrels per day of export capacity to the Pacific Coast narrowed the Western Canadian Select discount to WTI from a historical average of $15-20 to approximately $10-12 per barrel.

## LNG Canada
The LNG Canada project in Kitimat, British Columbia remained on track for first LNG cargo in mid-2025. The $40 billion project would provide the first direct access for Canadian natural gas to Asian markets, where LNG prices trade at a significant premium to North American benchmarks.

## Carbon Policy
Canada's carbon tax increased to $80 per tonne of CO2 equivalent in April 2024, on track to reach $170 by 2030. Energy producers have responded by accelerating carbon capture investments. The Pathways Alliance, a consortium of six major oil sands producers, continued development of a $16.5 billion carbon capture and storage project in northern Alberta.

## Dividend Yields
Canadian energy stocks offered among the highest dividend yields in the global energy sector. Companies like Canadian Natural Resources (5.1% yield), Suncor Energy (4.3%), and Enbridge (7.2%) attracted income-focused investors. Payout ratios were conservative, generally below 40% of free cash flow.
""",

    "portfolio_construction_ai.md": """# AI-Driven Portfolio Construction — Framework

## Summary
Incorporating AI exposure into traditional portfolios requires balancing the growth opportunity against concentration risk, valuation, and the cyclical nature of technology spending. This framework outlines approaches for different risk profiles.

## Direct AI Exposure
The most direct AI plays include semiconductor companies (NVIDIA, AMD, Broadcom), cloud infrastructure providers (Microsoft Azure, AWS, Google Cloud), and AI application companies. The challenge is that the most obvious beneficiaries are already priced for significant growth, with forward P/E ratios of 25-40x for the largest names.

## Indirect AI Beneficiaries
Companies that benefit from AI without being pure-play AI investments include utilities (data centre power demand), industrial REITs (data centre real estate), cooling companies (thermal management for GPUs), and enterprise software companies integrating AI features. These offer exposure at lower valuations.

## Risk Management
A diversified AI allocation should not exceed 15-20% of total equity exposure for most investors. Rebalancing quarterly prevents concentration drift. Stop-loss levels should account for the high volatility of AI-related stocks, with 25-30% drawdowns historically common even in secular uptrends.

## Portfolio Models
Conservative: 5% direct AI (broad semiconductor ETF) + 5% indirect (utility/infrastructure)
Moderate: 10% direct AI (mix of semiconductor and cloud) + 10% indirect
Aggressive: 20% direct AI (individual stocks) + 10% indirect + 5% crypto (BTC/ETH as digital infrastructure play)

## Evaluation Metrics
Track portfolio AI exposure through factor analysis. Monitor correlation between AI holdings — during the 2022 drawdown, AI stocks were highly correlated (0.8+), reducing diversification benefits. Aim for decorrelated AI exposure by mixing hardware, software, infrastructure, and indirect plays.
"""
}

for filename, content in documents.items():
    filepath = os.path.join(DOCS_DIR, filename)
    with open(filepath, "w") as f:
        f.write(content.strip())
    print(f"Created: {filepath}")

print(f"\nTotal documents: {len(documents)}")