# Google Drive & Photos Sync Application Setup

## Prerequisites

1. **Python 3.7 or higher** installed on your system
2. **Google Cloud Console access** to create API credentials
3. **Google account** with access to Google Drive and Google Photos

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set up Google API Credentials

### 2.1 Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Drive API
   - Google Photos Library API

### 2.2 Create OAuth 2.0 Credentials

1. In the Google Cloud Console, go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth 2.0 Client IDs**
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in the required application information
   - Add your email to test users
   - Add the following scopes:
     - `https://www.googleapis.com/auth/drive`
     - `https://www.googleapis.com/auth/photoslibrary`
     - `https://www.googleapis.com/auth/photoslibrary.sharing`
4. For the OAuth 2.0 Client ID:
   - Choose "Desktop application" as the application type
   - Give it a name (e.g., "Google Drive Photos Sync")
5. Download the credentials JSON file
6. Rename it to `credentials.json` and place it in the project directory

### 2.3 Important Security Notes

- **Never commit `credentials.json` to version control**
- **Never share your `credentials.json` file**
- The application will create a `token.pickle` file to store your authentication tokens
- Keep both files secure and private

## Step 3: Run the Application

```bash
python main.py
```

## Step 4: First-Time Setup

1. **Authentication**: Click the "Authenticate" button
   - Your web browser will open to Google's OAuth page
   - Sign in with your Google account
   - Grant the requested permissions
   - The application will save your authentication tokens

2. **Select Drive Folder**: Choose the Google Drive folder you want to sync
   - Only media files (images and videos) will be synced
   - The sync includes all subfolders recursively

3. **Start Sync**: Click "Start Sync" to begin the synchronization process

## How the Sync Works

### File Comparison
- Files are compared by **filename** and **creation date**
- Files with the same name and similar dates (within 24 hours) are considered matches
- Files with the same name but different dates trigger a conflict dialog

### Conflict Resolution
- When conflicts are detected, you'll see a dialog with file details
- You can choose whether files are the same or different
- "Same file" = no duplication, "Different files" = both are kept

### Sync Operations
- **Drive → Photos**: Files only in Drive are uploaded to Photos
- **Photos → Drive**: Files only in Photos are downloaded to Drive
- **Duplicates**: Prevented by the comparison logic

### Supported File Types
- **Images**: JPG, JPEG, PNG, GIF, BMP, WEBP, TIFF
- **Videos**: MP4, AVI, MOV, WMV, FLV, WEBM, MKV, M4V, 3GP, 3G2

## Troubleshooting

### Common Issues

1. **"Credentials file not found"**
   - Make sure `credentials.json` is in the project directory
   - Verify the file is not corrupted

2. **"Authentication failed"**
   - Check that the APIs are enabled in Google Cloud Console
   - Verify OAuth consent screen is configured
   - Try deleting `token.pickle` and re-authenticating

3. **"Access denied" errors**
   - Ensure your Google account has access to the Drive folder
   - Check that Photos API permissions are granted

4. **Upload/Download failures**
   - Check your internet connection
   - Verify file formats are supported
   - Large files may take time to process

### API Quotas and Limits

- Google Drive API: 1,000 requests per 100 seconds per user
- Google Photos API: 10,000 requests per day
- Large files may take time to upload/download
- The application includes automatic retry logic for rate limits

### File Size Limitations

- Google Photos: Individual files up to 200MB
- Google Drive: Individual files up to 5TB (with appropriate storage)
- Very large files may timeout during transfer

## Privacy and Security

- **Local Processing**: All file comparisons happen locally
- **No Data Storage**: The application doesn't store your files
- **OAuth Security**: Uses Google's secure OAuth 2.0 flow
- **Temporary Files**: Downloaded files are immediately cleaned up

## Support

If you encounter issues:
1. Check the application logs in the GUI
2. Verify your API credentials and permissions
3. Ensure all required APIs are enabled
4. Check Google Cloud Console for quota usage

## Limitations

- **Google Workspace Files**: Docs, Sheets, Slides are not synced
- **File Metadata**: Some metadata may not be preserved
- **Album Organization**: Photos are not organized into albums
- **Real-time Sync**: Manual sync only (not automatic)
- **Bandwidth**: Large libraries may take significant time to sync