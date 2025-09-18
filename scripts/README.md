# NFL Prediction Scripts

## process_nfl_html.py

Converts Neil Paine's NFL prediction HTML data into markdown format and saves it to the `data` folder.

### Usage

1. **From file:**
   ```bash
   python3 scripts/process_nfl_html.py input_file.txt
   ```

2. **From stdin (interactive):**
   ```bash
   python3 scripts/process_nfl_html.py
   # Then paste the HTML content and press Ctrl+D
   ```

### Input Format

The script expects HTML content in this format:

```
Predicted point spreads and win probabilities for Week X NFL games, based on PPG power ratings

Last updated: [Date and time]

Table with 5 columns and [N] rows. Sorted ascending by column "Win Prob." (column headers with buttons are sortable)
Date    Time (ET)    Matchup    Favorite    Win Prob.
[Game data rows...]
```

### Output

- Creates a file in `data/weekX_predictions.md`
- Extracts week number automatically from the HTML
- Parses matchups into away/home teams
- Parses favorite and spread information
- Preserves win probabilities and game times

### Example

Input:
```
Sun 9/21    1:00PM    Pittsburgh Steelers at New England Patriots    NE PK    50%
```

Output markdown table row:
```
| Sun 9/21 | 1:00PM | Pittsburgh Steelers | New England Patriots | NE | PK | 50% |
```

## Features

- ✅ Automatic week number detection
- ✅ Parses team matchups (away @ home)
- ✅ Extracts spreads and favorites
- ✅ Preserves win probabilities
- ✅ Handles pick'em games (PK)
- ✅ Creates clean markdown tables
- ✅ Saves to organized data folder