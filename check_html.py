with open('uraas/dashboard/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

script_start = content.find('<script>', 22000)
script_content = content[script_start+8:content.find('</script>', script_start)]

opens = script_content.count('{')
closes = script_content.count('}')
print(f'Braces: {opens} open, {closes} close, diff={opens-closes}')

fns = ['toggleTheme','switchTab','loadAnalytics','loadImpactCards','switchAnalyticsTab',
       'runFacultyComparison','loadNetworkTab','loadTrendsTab','loadLanguageTab',
       'loadLecturerProfile','chartDefaults','fetchOverview','renderTree',
       'openPaperModal','startCrawler','runSearch','debounceSearch']
for fn in fns:
    status = 'OK' if fn in script_content else 'MISSING'
    print(f'  {status}: {fn}')

# Check HTML elements referenced in JS
elements = ['atab-overview','atab-compare','atab-network','atab-trends',
            'atab-language','atab-lecturer','atab-search','impact-cards',
            'chart-year','chart-faculty','chart-oa','chart-authors',
            'chart-faculty-oa','chart-growth','network-table',
            'chart-dept-compare','chart-network-authors','chart-trends',
            'chart-language-kw','language-papers','lecturer-profile-result',
            'author-suggestions','faculty-comparison-result']
print('\nHTML elements:')
for el in elements:
    status = 'OK' if f'id="{el}"' in content else 'MISSING'
    print(f'  {status}: #{el}')
