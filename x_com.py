from curl_cffi import requests
from bs4 import BeautifulSoup
import json, re

def _fxtwitter_fallback(session: requests.Session, url: str): # until i find a way to get nsfw shit from guest + better than nothing at all
    fx_url = url.replace("//x.com", "//api.fxtwitter.com")
    resp = session.get(fx_url)
    if not resp.status_code == 200:
        raise Exception("[X.COM] FxTwitter returned", resp.status_code)
    data = resp.json()
    tweet = data["tweet"]
    all_media = [media["url"] for media in tweet["media"]["all"]]
    return all_media

def x_com_fetch(session: requests.Session, url: str):
    TweetIdMatch = re.search(r'/[^/]+/status/(\d+)', url)
    if not TweetIdMatch:
        raise Exception("[X.COM] Tweet id failed to regex? The fuck are you doing?")
    
    TweetId = TweetIdMatch.group(1)
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    GuestTokenMatch = re.search(r'<script\s+nonce="[^"]*".*?gt=(\d+);', resp.text, re.DOTALL)
    if not GuestTokenMatch:
        raise Exception("[X.COM] Failed to find Guest Token.")

    GuestToken = GuestTokenMatch.group(1)

    link_tag = soup.find("link", href=lambda x: x and "main." in x)

    if not link_tag:
        raise Exception("[X.COM] Failed to extract js link.")
    js_resp = session.get(link_tag['href'])
    QueryIdPattern = r'queryId:\s*"([^"]+)"(?=[^}]*operationName:\s*"TweetResultByRestId")'
    QueryIdMatch = re.search(QueryIdPattern, js_resp.text)
    if not QueryIdMatch:
        raise Exception("[X.COM] Failed to find Query Id.")
    QueryId = QueryIdMatch.group(1)

    # prepare headers
    BearerTokenPattern = r'const\s+e\s*=\s*"([^"]+)"(?=.*Bearer token)'
    BearerTokenMatch = re.search(BearerTokenPattern, js_resp.text, re.DOTALL)

    if not BearerTokenMatch:
        BearerTokenPattern2 = r'const\s+n\s*=\s*new\s*Map\s*,\s*t\s*=\s*"([^"]+)";\s*n\.set\("Authorization",\s*`Bearer\s*\$\{t\}`\)'
        BearerTokenMatch = re.search(BearerTokenPattern2, js_resp.text, re.DOTALL)

    if not BearerTokenMatch:
        raise Exception("[X.COM] Bearer token not found.")

    BearerToken = BearerTokenMatch.group(1)

    session.headers["authorization"] = f"Bearer {BearerToken}"
    session.headers["x-guest-token"] = GuestToken
    session.headers["x-twitter-active-user"] = "yes"
    session.headers["x-twitter-client-language"] = "en"
    
    # build api url
    variables = {
        "tweetId": TweetId,
        "with_rux_injections": False,
        "withCommunity": False,
        "includePromotedContent": False,
        "withVoice": False
    }

    features = {
        "rweb_xchat_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "premium_content_api_read_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
        "responsive_web_grok_analyze_post_followups_enabled": False,
        "responsive_web_jetfuel_frame": True,
        "responsive_web_grok_share_attachment_enabled": True,
        "articles_preview_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "responsive_web_grok_show_grok_translated_post": False,
        "responsive_web_grok_analysis_button_from_backend": True,
        "creator_subscriptions_quote_tweet_preview_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "payments_enabled": False,
        "profile_label_improvements_pcf_label_in_post_enabled": True,
        "rweb_tipjar_consumption_enabled": True,
        "verified_phone_label_enabled": False,
        "responsive_web_grok_image_annotation_enabled": True,
        "responsive_web_grok_imagine_annotation_enabled": True,
        "responsive_web_grok_community_note_auto_translation_is_enabled": False,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_enhance_cards_enabled": False,
        "responsive_web_profile_redirect_enabled": True
    }

    fieldToggles = {
        "withArticleRichContentState": True,
        "withArticlePlainText": False,
        "withGrokAnalyze": False,
        "withDisallowedReplyControls": False
    }

    # Build the URL
    graphql_url = (
        f'https://api.x.com/graphql/{QueryId}/TweetResultByRestId'
        f'?variables={json.dumps(variables)}'
        f'&features={json.dumps(features)}'
        f'&fieldToggles={json.dumps(fieldToggles)}'
    )
    
    resp = session.get(graphql_url)
    data = resp.json().get("data")
    if not data:
        raise Exception(f"[X.COM] GraphQL response missing 'data': {resp.text}")
    if "Age-restricted adult content. This content might not be appropriate for people under 18 years old. To view this media, you’ll need to log in to X. Learn more" in resp.text:
        #raise Exception("[X.COM] Age-restricted. This content might not be appropriate for people under 18 years old.")
        # Fallback to fxtwitter API im not going to fight twitters auth only nsfw bullshit
        # https://github.com/FxEmbed/FxEmbed/wiki/Status-Fetch-API
        return _fxtwitter_fallback(session, url)
    
    SCRAPED_LINKS = []

    medias_data = data["tweetResult"]["result"]["legacy"]["entities"]["media"]
    for media in medias_data:
        media_type = media["type"]
        if media_type == "video": # Checks if there is a video present.
            variants = media["video_info"]["variants"]
            mp4_variants = [v for v in variants if v.get("content_type") == "video/mp4" and "bitrate" in v]
            if not mp4_variants:
                raise Exception("[X.COM] No mp4 variants found.")
            highest_quality = max(mp4_variants, key=lambda x: x["bitrate"])
            highest_quality_url = highest_quality["url"]
            SCRAPED_LINKS.append(highest_quality_url)
        elif media_type == "photo":
            SCRAPED_LINKS.append(media["media_url_https"])
            
    return SCRAPED_LINKS
