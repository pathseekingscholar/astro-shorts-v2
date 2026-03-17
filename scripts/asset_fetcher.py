"""
V5 Asset Fetcher - Music by Mood
================================
Downloads free music from Pixabay based on video mood.
Optionally downloads background images (requires API key).
"""

import os
import json
import random
import requests
import hashlib

# =============================================================================
# MUSIC LIBRARY - Free Pixabay Tracks
# =============================================================================
MUSIC_LIBRARY = {
    "epic": [
        {"name": "epic_cinematic_01", "url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"},
        {"name": "epic_adventure_02", "url": "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946bc53789.mp3"},
        {"name": "epic_trailer_03", "url": "https://cdn.pixabay.com/download/audio/2022/02/22/audio_d1718ab41b.mp3"},
    ],
    "dramatic": [
        {"name": "dramatic_tension_01", "url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_8cb749d484.mp3"},
        {"name": "dramatic_suspense_02", "url": "https://cdn.pixabay.com/download/audio/2021/08/04/audio_bb630a7a4d.mp3"},
    ],
    "cinematic": [
        {"name": "cinematic_documentary_01", "url": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bab.mp3"},
        {"name": "cinematic_inspiring_02", "url": "https://cdn.pixabay.com/download/audio/2022/05/16/audio_1d2b3f8c0e.mp3"},
    ],
    "intense": [
        {"name": "intense_action_01", "url": "https://cdn.pixabay.com/download/audio/2022/03/10/audio_2dde668d05.mp3"},
        {"name": "intense_powerful_02", "url": "https://cdn.pixabay.com/download/audio/2021/11/25/audio_cb5a6a1cc0.mp3"},
    ],
    "mind-blowing": [
        {"name": "epic_discovery_01", "url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"},
        {"name": "wonder_space_02", "url": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bab.mp3"},
    ],
    "chill": [
        {"name": "lofi_chill_01", "url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_d0c1975323.mp3"},
        {"name": "ambient_space_02", "url": "https://cdn.pixabay.com/download/audio/2022/01/20/audio_d16737dc28.mp3"},
    ],
    "horror": [
        {"name": "dark_ambient_01", "url": "https://cdn.pixabay.com/download/audio/2021/08/08/audio_dc39bde808.mp3"},
        {"name": "scary_tension_02", "url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_8cb749d484.mp3"},
    ],
}

# Fallback mood
DEFAULT_MOOD = "cinematic"

# =============================================================================
# FUNCTIONS
# =============================================================================
def download_music(mood, output_dir="assets/audio"):
    """
    Download music matching the mood.
    
    Args:
        mood: One of: epic, dramatic, cinematic, intense, mind-blowing, chill, horror
        output_dir: Where to save music
    
    Returns:
        Path to downloaded music, or None if failed
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Normalize mood
    mood = mood.lower().strip().replace(" ", "-")
    
    # Find tracks
    tracks = MUSIC_LIBRARY.get(mood)
    if not tracks:
        # Try to find similar mood
        for key in MUSIC_LIBRARY:
            if key in mood or mood in key:
                tracks = MUSIC_LIBRARY[key]
                break
    
    if not tracks:
        print(f"⚠️ Unknown mood '{mood}', using default")
        tracks = MUSIC_LIBRARY.get(DEFAULT_MOOD, [])
    
    if not tracks:
        print(f"❌ No music tracks available")
        return None
    
    # Pick random track
    track = random.choice(tracks)
    track_name = track["name"]
    track_url = track["url"]
    
    # Check if already exists
    output_path = os.path.join(output_dir, f"{track_name}.mp3")
    if os.path.exists(output_path):
        print(f"📦 Using cached: {track_name}")
        return output_path
    
    # Download
    try:
        print(f"🎵 Downloading: {track_name} ({mood} mood)...")
        response = requests.get(track_url, timeout=120)
        
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f"✅ Downloaded: {output_path} ({size_mb:.1f} MB)")
            return output_path
        else:
            print(f"❌ Download failed: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Download error: {e}")
        return None


def download_image(query, pixabay_api_key, output_dir="assets/images"):
    """
    Download image from Pixabay.
    
    Args:
        query: Search query (e.g., "galaxy nebula space")
        pixabay_api_key: Your Pixabay API key
        output_dir: Where to save images
    
    Returns:
        Path to downloaded image, or None if failed
    """
    if not pixabay_api_key:
        print(f"⚠️ No Pixabay API key, skipping image download")
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename from query hash
    query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
    output_path = os.path.join(output_dir, f"{query_hash}.jpg")
    
    # Check cache
    if os.path.exists(output_path):
        print(f"📦 Using cached image for '{query}'")
        return output_path
    
    try:
        print(f"🔍 Searching Pixabay: {query}...")
        
        params = {
            "key": pixabay_api_key,
            "q": query,
            "image_type": "photo",
            "orientation": "vertical",
            "min_width": 1080,
            "safesearch": "true",
            "per_page": 5,
        }
        
        response = requests.get("https://pixabay.com/api/", params=params, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Pixabay API error: {response.status_code}")
            return None
        
        hits = response.json().get("hits", [])
        
        if not hits:
            print(f"❌ No images found for '{query}'")
            return None
        
        # Get best image
        image_url = hits[0].get("largeImageURL") or hits[0].get("webformatURL")
        
        if not image_url:
            print(f"❌ No image URL in response")
            return None
        
        # Download image
        print(f"⬇️ Downloading image...")
        img_response = requests.get(image_url, timeout=60)
        
        if img_response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(img_response.content)
            print(f"✅ Downloaded: {output_path}")
            return output_path
        else:
            print(f"❌ Image download failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def fetch_assets_for_script(script_data, pixabay_api_key=None):
    """
    Fetch all assets needed for a video script.
    
    Args:
        script_data: The full script data with metadata
        pixabay_api_key: Optional Pixabay API key for images
    
    Returns:
        Dict with paths: {"music": path, "background": path}
    """
    assets = {
        "music": None,
        "background": None,
    }
    
    metadata = script_data.get("metadata", {})
    
    # Get music
    mood = metadata.get("music_style") or metadata.get("mood") or "cinematic"
    assets["music"] = download_music(mood)
    
    # Get background image (optional)
    if pixabay_api_key:
        bg_search = metadata.get("background_search", "")
        if bg_search:
            assets["background"] = download_image(bg_search, pixabay_api_key)
    
    return assets


# =============================================================================
# MAIN (for testing)
# =============================================================================
def main():
    print("=" * 60)
    print("🎵 Asset Fetcher Test")
    print("=" * 60)
    
    # Test music download
    print("\nTesting music download...")
    for mood in ["epic", "dramatic", "chill"]:
        path = download_music(mood)
        if path:
            print(f"  ✅ {mood}: {path}")
        else:
            print(f"  ❌ {mood}: failed")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
