#!/usr/bin/env python3
"""
Script to process NFL predictions HTML and convert to markdown format.
Extracts week number and saves to data folder.
"""

import re
import sys
from datetime import datetime

def extract_week_number(html_content):
    """Extract the week number from the HTML content."""
    # Look for "Week X" pattern
    week_match = re.search(r'Week (\d+)', html_content, re.IGNORECASE)
    if week_match:
        return int(week_match.group(1))
    return None

def parse_html_table(html_content):
    """Parse the HTML table format and extract game data."""
    lines = html_content.strip().split('\n')
    
    # Find the table header line
    header_line = None
    data_start = None
    
    for i, line in enumerate(lines):
        if 'Date' in line and 'Time' in line and 'Matchup' in line:
            header_line = line
            data_start = i + 1
            break
    
    if not header_line or data_start is None:
        raise ValueError("Could not find table header in HTML content")
    
    # Parse header to understand column positions
    headers = ['Date', 'Time (ET)', 'Matchup', 'Favorite', 'Win Prob.']
    
    # Extract game data
    games = []
    for i in range(data_start, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
            
        # Split by tabs or multiple spaces
        parts = re.split(r'\t+|\s{2,}', line)
        
        if len(parts) >= 5:
            game = {
                'date': parts[0],
                'time': parts[1],
                'matchup': parts[2],
                'favorite': parts[3],
                'win_prob': parts[4]
            }
            games.append(game)
    
    return games

def parse_matchup(matchup_text):
    """Parse matchup text to extract away and home teams."""
    # Format: "Team A at Team B"
    if ' at ' in matchup_text:
        away, home = matchup_text.split(' at ', 1)
        return away.strip(), home.strip()
    return matchup_text.strip(), ""

def parse_favorite_spread(favorite_text):
    """Parse favorite and spread from the favorite column."""
    # Examples: "NE PK", "BAL -4.5", "WSH -9"
    if ' PK' in favorite_text:
        team = favorite_text.replace(' PK', '').strip()
        return team, "PK"
    elif ' -' in favorite_text:
        parts = favorite_text.split(' -')
        team = parts[0].strip()
        spread = '-' + parts[1].strip()
        return team, spread
    elif ' +' in favorite_text:
        parts = favorite_text.split(' +')
        team = parts[0].strip()
        spread = '+' + parts[1].strip()
        return team, spread
    else:
        return favorite_text.strip(), ""

def create_markdown_table(games, week_number, last_updated):
    """Create markdown table from game data."""
    markdown = f"# Week {week_number} NFL Game Predictions - Neil Paine ELO Ratings\n\n"
    markdown += f"*Source: Neil Paine's NFL Power Ratings*\n"
    markdown += f"*Last Updated: {last_updated}*\n\n"
    
    # Create table header
    markdown += "| Date | Time | Away Team | Home Team | Favorite | Spread | Win Prob |\n"
    markdown += "|------|------|-----------|-----------|----------|--------|-----------|\n"
    
    # Add data rows
    for game in games:
        away, home = parse_matchup(game['matchup'])
        fav_team, spread = parse_favorite_spread(game['favorite'])
        
        markdown += f"| {game['date']} | {game['time']} | {away} | {home} | {fav_team} | {spread} | {game['win_prob']} |\n"
    
    return markdown

def extract_last_updated(html_content):
    """Extract the last updated timestamp from HTML."""
    # Look for "Last updated: ..." pattern
    updated_match = re.search(r'Last updated:\s*(.+?)(?:\n|$)', html_content)
    if updated_match:
        return updated_match.group(1).strip()
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def main():
    print("NFL HTML to Markdown Converter")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        # Read from file if provided
        input_file = sys.argv[1]
        try:
            with open(input_file, 'r') as f:
                html_content = f.read()
        except FileNotFoundError:
            print(f"Error: File '{input_file}' not found")
            sys.exit(1)
    else:
        # Read from stdin
        print("Paste the HTML content below, then press Ctrl+D (Mac/Linux) or Ctrl+Z (Windows):")
        html_content = sys.stdin.read()
    
    if not html_content.strip():
        print("Error: No content provided")
        sys.exit(1)
    
    try:
        # Extract week number
        week_number = extract_week_number(html_content)
        if not week_number:
            print("Error: Could not find week number in content")
            sys.exit(1)
        
        # Extract last updated timestamp
        last_updated = extract_last_updated(html_content)
        
        # Parse the table data
        games = parse_html_table(html_content)
        
        if not games:
            print("Error: No game data found")
            sys.exit(1)
        
        # Create markdown content
        markdown_content = create_markdown_table(games, week_number, last_updated)
        
        # Save to data folder
        output_file = f"data/week{week_number}_predictions.md"
        with open(output_file, 'w') as f:
            f.write(markdown_content)
        
        print(f"✅ Successfully processed {len(games)} games")
        print(f"✅ Saved to: {output_file}")
        print(f"✅ Week {week_number} predictions ready")
        
        # Show preview
        print("\n" + "=" * 60)
        print("PREVIEW:")
        print("=" * 60)
        print(markdown_content[:800] + "..." if len(markdown_content) > 800 else markdown_content)
        
    except Exception as e:
        print(f"Error processing content: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()