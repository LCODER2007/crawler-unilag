# CRAWLER INSTRUCTIONS

## IMPORTANT: Use the RIGHT Crawler!

You have been running the WRONG crawler! That's why it stops after only 250-350 candidates.

### WRONG Crawler (stops early):
```bash
python crawl_10_validated.py --target 10
```

### CORRECT Crawler (searches up to 100,000 pages):
```bash
python crawl_aggressive.py --target 10
```

Or use the launcher:
```bash
python run_aggressive_crawler.py --target 10
```

## Why the Difference?

- **crawl_10_validated.py**: Old crawler that gives up after ~250-350 candidates
- **crawl_aggressive.py**: New crawler that searches up to 100,000 pages until target is reached
- **run_aggressive_crawler.py**: Simple launcher for the aggressive crawler

## Examples:

```bash
# Get 10 papers (will search thousands of pages if needed)
python crawl_aggressive.py --target 10

# Get 50 papers (will search thousands of pages if needed)  
python crawl_aggressive.py --target 50

# Get 100 papers (will search thousands of pages if needed)
python crawl_aggressive.py --target 100
```

## What to Expect:

The aggressive crawler will:
- Search through thousands of pages
- Not stop until target is reached
- Show clear progress messages
- Continue even if many duplicates/no-matches found
- Only stop when target papers are stored OR 100,000 pages reached

## Chart Loading Fixed Too!

The "Load Charts" button in Analytics -> Overview has been fixed and will no longer get stuck on "Loading...".