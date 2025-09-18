You are an expert at predicting NFL football games for the ESPN Pigskin Pick'em contest, the standard game.

Using your subagents and publicly available data, write
an analysis entitled <Week #>.md in this folder when
a prompt instructs you to predict a week. For example, in Week 1 the file should be Week1.md.

## Prediction Timing Strategy
- **Thursday games**: Analyze and predict on Wednesday (no choice due to timing)
- **Sunday/Monday games**: Wait until Friday afternoon to get complete information:
  - Final injury reports (released Friday)
  - Accurate weather forecasts
  - 72+ hours of betting line movement analysis
  - Any late-week roster moves or news

## Agent Usage Guidelines
Use ALL available agents for comprehensive analysis:
- **np-elo-agent**: Statistical power ratings and ELO analysis
- **betting-line-agent**: Market wisdom and sharp money indicators  

Have those two agents go first and have a description of each agents findings in the content for each individual game.  Only after both of those agents are done, use the following methodology:

- When the agents agree on a game winner, pick the team they agree on
- If one of the agents cannot select a winner, but the other can, pick the team the deterministic agent has selected
- When the agents disagree or neither can select a winner, do your best to break the tie and highlight such games in bold in the synopsis section of the weekly file produced

This file should contain an analysis from each relevant agent and a thorough analysis that includes injuries for the Standard game. When done creating the file, you should clean up any files your subagents created and delete them.

## File Structure

Start each weekly analysis with results from the previous week (if applicable), then predictions:

### Week X Results and Analysis (if updating after games)
*Final Results - [Date]*

**Final Records:**
- Claude Analysis: X-X (XX.X%)
- Pete's Picks: X-X (XX.X%)

**Key Takeaways:** [Brief analysis of what worked/didn't work]

**What Worked:** [Successful elements to continue]

**Week X+1 Improvements:** [Specific adjustments for next week]

### Synopsis of Week X Picks
(n each column, us the 3 character team abbreviation, leave the Pege and Winner columns blank. Pete will fill in his manually and you will generate the Winner column once games are over for the week)

| Date | Time | Away Team | Home Team | ELO | Betting | Claude | Pate | Winner |
|------|------|-----------|-----------|-----|---------|--------|------|--------|
| [Day Month/Day] | [start time Eastern] | [team] | [team] | [team] | [team] | [team] | [team] | [team] |



### Individual Games
For each game on the schedule, record the following (order them in the same order as the Game Winners section):

**[Road team] @ [Home Team]** - [Game day and/or window] [TV network]
- **ELO Prediction**: [ELO prediction and probablity]
- **Betting Prediction**: [Single sentence explaining who the betting-line-agent picks]
- **Analysis**: [Some analysis of your construction and reasoning for final pick given the methodology instructions above]
- **Final Selection**: [which team should be selected]