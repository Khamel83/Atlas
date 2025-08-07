# Instapaper Integration Guide

**Last Updated**: August 2025

## 🎯 Overview

Atlas provides comprehensive Instapaper integration to backup and process your complete reading collection. This guide covers both CSV export processing (recommended) and API extraction methods.

## 🚀 Quick Start

### Method 1: CSV Export (Recommended)

**Best for**: Complete historical backup of your entire Instapaper collection

1. **Export from Instapaper**:
   - Go to [Instapaper Settings](https://www.instapaper.com/user)
   - Click "Export" to download your CSV file
   - Save as `inputs/instapaper_export.csv`

2. **Convert to Atlas format**:
   ```bash
   python3 csv_to_atlas_converter.py
   ```

3. **Results**:
   - Complete collection converted to Atlas format
   - All metadata preserved (folders, timestamps, selections)
   - Both web bookmarks and private content processed

### Method 2: API Extraction

**Best for**: Recent bookmarks with full article content

1. **Setup credentials** in `.env`:
   ```bash
   INSTAPAPER_CONSUMER_KEY=your_key
   INSTAPAPER_CONSUMER_SECRET=your_secret
   INSTAPAPER_USERNAME=your_email
   INSTAPAPER_PASSWORD=your_password
   ```

2. **Run extraction**:
   ```bash
   python3 instapaper_complete_extraction.py
   ```

## 📊 Comparison: CSV vs API

| Feature | CSV Export | API Extraction |
|---------|------------|----------------|
| **Coverage** | Complete collection (6,000+ items) | Recent ~500 bookmarks only |
| **Content** | Titles, URLs, metadata | Full article content + metadata |
| **Private Content** | Newsletters, emails included | Not accessible |
| **Historical Data** | Full 10+ year history | Recent items only |
| **Setup** | Simple export from web | API credentials required |
| **Recommendation** | ✅ Primary method | 🔄 Supplement for recent content |

## 🔍 Technical Details

### API Limitations Discovered

Through extensive testing, we found:

1. **500-Bookmark Limit**: API returns only the latest ~500 bookmarks across your entire account
2. **Cross-Folder Duplication**: Same bookmarks appear in all folders
3. **No Historical Access**: Older bookmarks (6+ months) not accessible via API
4. **Subscription Status**: Even with active subscription, historical data remains limited

### CSV Structure

The CSV export contains:
- **Web URLs**: Standard HTTP/HTTPS bookmarks
- **Private Content**: `instapaper-private://email/` entries for newsletters
- **Metadata**: Title, folder, timestamp, selections, tags

## 📁 Output Structure

Both methods create Atlas-compatible files:

```
output/articles/
├── html/           # HTML files with full formatting
├── markdown/       # Clean markdown content  
└── metadata/       # JSON metadata files
```

Each bookmark gets:
- **Unique ID**: Generated from URL + title + timestamp
- **Complete Metadata**: All original Instapaper data preserved
- **Atlas Format**: Compatible with Atlas processing pipeline

## 🛠️ Available Scripts

### Core Scripts

- **`csv_to_atlas_converter.py`**: Convert CSV export to Atlas format
- **`instapaper_complete_extraction.py`**: API extraction with pagination
- **`helpers/instapaper_api_client.py`**: API client implementation

### Analysis & Testing Scripts

- **`comprehensive_api_analysis.py`**: Analyze API capabilities and limitations
- **`investigate_bookmark_duplication.py`**: Deep dive into API behavior
- **`test_folder_management.py`**: Test folder operations
- **`compare_csv_vs_api.py`**: Compare extraction methods

## 📋 Example Usage

### Complete CSV Processing

```bash
# Place your CSV export in inputs/
cp ~/Downloads/instapaper-export.csv inputs/instapaper_export.csv

# Convert to Atlas format
python3 csv_to_atlas_converter.py

# Results
echo "Processed $(ls output/articles/html/*.html | wc -l) bookmarks"
```

### API Extraction

```bash
# Set up credentials
echo 'INSTAPAPER_CONSUMER_KEY=your_key' >> .env
echo 'INSTAPAPER_CONSUMER_SECRET=your_secret' >> .env
echo 'INSTAPAPER_USERNAME=your_email' >> .env
echo 'INSTAPAPER_PASSWORD=your_password' >> .env

# Extract recent bookmarks
python3 instapaper_complete_extraction.py

# Convert to Atlas format
python3 convert_instapaper_to_atlas.py
```

## 🎯 Recommendations

### For Complete Backup
1. **Use CSV export** as your primary method
2. **Supplement with API** for recent content with full text
3. **Process both** and deduplicate if needed

### For Ongoing Sync
1. **Initial CSV import** for historical content
2. **Regular API extraction** for new bookmarks
3. **Automated processing** with Atlas pipeline

## ⚠️ Important Notes

### Privacy & Security
- **Local Processing**: All data stays on your machine
- **API Credentials**: Stored in local `.env` file only
- **No Cloud Dependencies**: Direct Instapaper integration only

### Known Limitations
- **API Historical Limit**: Cannot access bookmarks older than ~6 months
- **Content Fetching**: CSV method doesn't include full article content
- **Rate Limiting**: API extraction includes delays to respect Instapaper's limits

## 🔧 Troubleshooting

### Common Issues

**"CSV file not found"**
- Ensure file is named `inputs/instapaper_export.csv`
- Check file permissions and encoding

**"Authentication failed"**
- Verify API credentials in `.env`
- Check Instapaper account status
- Ensure consumer key/secret are valid

**"Only getting 500 bookmarks"**
- This is expected API behavior for historical collections
- Use CSV export method for complete backup

### Getting Help

1. **Check logs**: Look in processing output for error details
2. **Validate setup**: Run analysis scripts to diagnose issues
3. **Compare methods**: Use comparison scripts to understand coverage

## 📈 Future Enhancements

Planned improvements:
- **Hybrid processing**: Combine CSV metadata with API content
- **Incremental updates**: Smart detection of new bookmarks
- **Content enrichment**: Full article fetching for CSV bookmarks
- **Search integration**: Full-text search across processed bookmarks

---

**Last Tested**: August 2025 with Instapaper Premium account
**Coverage**: 6,239 bookmarks processed successfully (100% success rate)