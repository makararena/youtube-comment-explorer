from __future__ import print_function

import json
import re
import time

from ytce.youtube.extractors import extract_ytcfg, extract_ytinitialdata
from ytce.youtube.html import fetch_html
from ytce.youtube.innertube import inertube_ajax_request
from ytce.youtube.pagination import search_dict
from ytce.youtube.session import make_session

YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v={youtube_id}"

SORT_BY_POPULAR = 0
SORT_BY_RECENT = 1


class YoutubeCommentDownloader:

    def __init__(self):
        self.session = make_session()

    def ajax_request(self, endpoint, ytcfg, retries=5, sleep=20, timeout=60):
        return inertube_ajax_request(
            self.session, endpoint, ytcfg, retries=retries, sleep=float(sleep), timeout=timeout
        )

    def get_comments(self, youtube_id, *args, **kwargs):
        return self.get_comments_from_url(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id), *args, **kwargs)

    def _extract_comment_count(self, data):
        """Extract total comment count from YouTube response data."""
        # Try multiple possible locations for comment count
        # 1. Look for commentCountRenderer
        count_renderer = next(search_dict(data, "commentCountRenderer"), None)
        if count_renderer:
            count_text = count_renderer.get("text", {})
            if count_text:
                runs = count_text.get("runs", [])
                if runs:
                    count_str = runs[0].get("text", "")
                    parsed = self._parse_comment_count(count_str)
                    if parsed:
                        return parsed
                simple_text = count_text.get("simpleText", "")
                if simple_text:
                    parsed = self._parse_comment_count(simple_text)
                    if parsed:
                        return parsed
        
        # 2. Look for headerRenderer with count
        header = next(search_dict(data, "headerRenderer"), None)
        if header:
            count_text = header.get("countText", {})
            if count_text:
                runs = count_text.get("runs", [])
                if runs:
                    count_str = runs[0].get("text", "")
                    parsed = self._parse_comment_count(count_str)
                    if parsed:
                        return parsed
                simple_text = count_text.get("simpleText", "")
                if simple_text:
                    parsed = self._parse_comment_count(simple_text)
                    if parsed:
                        return parsed
        
        # 3. Look for commentsHeaderRenderer with title/countText
        comments_header = next(search_dict(data, "commentsHeaderRenderer"), None)
        if comments_header:
            # Check for countText in header
            count_text = comments_header.get("countText", {})
            if count_text:
                runs = count_text.get("runs", [])
                if runs:
                    count_str = runs[0].get("text", "")
                    parsed = self._parse_comment_count(count_str)
                    if parsed:
                        return parsed
                simple_text = count_text.get("simpleText", "")
                if simple_text:
                    parsed = self._parse_comment_count(simple_text)
                    if parsed:
                        return parsed
            
            # Check title which might contain count
            title = comments_header.get("title", {})
            if title:
                runs = title.get("runs", [])
                if runs:
                    for run in runs:
                        text = run.get("text", "")
                        parsed = self._parse_comment_count(text)
                        if parsed:
                            return parsed
                simple_text = title.get("simpleText", "")
                if simple_text:
                    parsed = self._parse_comment_count(simple_text)
                    if parsed:
                        return parsed
        
        # 4. Look for commentCount in various places
        comment_count = next(search_dict(data, "commentCount"), None)
        if comment_count:
            if isinstance(comment_count, (int, float)):
                return int(comment_count)
            if isinstance(comment_count, str):
                parsed = self._parse_comment_count(comment_count)
                if parsed:
                    return parsed
        
        # 5. Search all text fields for comment count patterns
        # This is a fallback - look for text containing numbers and "comment"
        for text_field in search_dict(data, "text"):
            if isinstance(text_field, dict):
                runs = text_field.get("runs", [])
                if runs:
                    for run in runs:
                        text = run.get("text", "")
                        if "comment" in text.lower() and any(c.isdigit() for c in text):
                            parsed = self._parse_comment_count(text)
                            if parsed:
                                return parsed
                simple_text = text_field.get("simpleText", "")
                if simple_text and "comment" in simple_text.lower() and any(c.isdigit() for c in simple_text):
                    parsed = self._parse_comment_count(simple_text)
                    if parsed:
                        return parsed
        
        return None
    
    def _parse_comment_count(self, count_str):
        """Parse comment count string to integer."""
        if not count_str:
            return None
        
        # Remove common text
        count_str = count_str.lower().replace("comments", "").replace("comment", "").strip()
        
        # Handle formats like "28,999" or "28.9K" or "1.2M"
        # First, check for K/M/B suffix before removing dots
        multiplier = 1
        original_str = count_str
        if count_str.endswith("k"):
            multiplier = 1000
            count_str = count_str[:-1]
        elif count_str.endswith("m"):
            multiplier = 1000000
            count_str = count_str[:-1]
        elif count_str.endswith("b"):
            multiplier = 1000000000
            count_str = count_str[:-1]
        
        # Remove commas
        count_str = count_str.replace(",", "")
        
        try:
            # Try to extract number - handle decimal formats like "28.9K"
            if "." in count_str and multiplier > 1:
                # Handle "28.9K" -> 28.9 * 1000 = 28900
                base_num = float(count_str)
                return int(base_num * multiplier)
            else:
                # Handle integer formats like "28999" or "28,999"
                return int(float(count_str) * multiplier)
        except (ValueError, TypeError):
            # Fallback: try regex to extract any numbers
            numbers = re.findall(r'\d+', original_str)
            if numbers:
                try:
                    base_num = float(numbers[0])
                    if len(numbers) > 1 and "." in original_str:
                        # Handle "28.9K" format with regex fallback
                        decimal_part = float(numbers[1]) / (10 ** len(numbers[1]))
                        base_num = float(numbers[0]) + decimal_part
                    return int(base_num * multiplier)
                except (ValueError, IndexError):
                    pass
        
        return None

    def get_comments_from_url(self, youtube_url, sort_by=SORT_BY_RECENT, language=None, sleep=.1):
        html, _final_url = fetch_html(self.session, youtube_url, timeout=30)
        ytcfg = extract_ytcfg(html)
        if language:
            ytcfg["INNERTUBE_CONTEXT"]["client"]["hl"] = language

        data = extract_ytinitialdata(html)

        item_section = next(search_dict(data, "itemSectionRenderer"), None)
        renderer = next(search_dict(item_section, "continuationItemRenderer"), None) if item_section else None
        if not renderer:
            # Comments disabled?
            return

        sort_menu = next(search_dict(data, "sortFilterSubMenuRenderer"), {}).get("subMenuItems", [])
        if not sort_menu:
            # No sort menu. Maybe this is a request for community posts?
            section_list = next(search_dict(data, "sectionListRenderer"), {})
            continuations = list(search_dict(section_list, "continuationEndpoint"))
            # Retry..
            data = self.ajax_request(continuations[0], ytcfg) if continuations else {}
            sort_menu = next(search_dict(data, "sortFilterSubMenuRenderer"), {}).get("subMenuItems", [])
        if not sort_menu or sort_by >= len(sort_menu):
            raise RuntimeError("Failed to set sorting")
        continuations = [sort_menu[sort_by]["serviceEndpoint"]]

        # Extract total comment count from initial data
        total_comment_count = self._extract_comment_count(data)
        
        # Make first API call to get comments and potentially better count info
        first_response = None
        if continuations:
            first_response = self.ajax_request(continuations[0], ytcfg)
            if first_response:
                # Try to get count from first response too
                if total_comment_count is None:
                    total_comment_count = self._extract_comment_count(first_response)
                # Process first response
                continuations = continuations[1:]  # Remove the one we just processed
            else:
                # If first request failed, put it back
                first_response = None

        # Yield total count first if available
        if total_comment_count is not None:
            yield {"_total_count": total_comment_count}

        # Process first response if we have it
        if first_response:
            error = next(search_dict(first_response, "externalErrorMessage"), None)
            if error:
                raise RuntimeError("Error returned from server: " + error)

            actions = list(search_dict(first_response, "reloadContinuationItemsCommand")) + \
                      list(search_dict(first_response, "appendContinuationItemsAction"))
            for action in actions:
                for item in action.get("continuationItems", []):
                    if action["targetId"] in ["comments-section",
                                              "engagement-panel-comments-section",
                                              "shorts-engagement-panel-comments-section"]:
                        # Process continuations for comments and replies.
                        continuations[:0] = [ep for ep in search_dict(item, "continuationEndpoint")]
                    if action["targetId"].startswith("comment-replies-item") and "continuationItemRenderer" in item:
                        # Process the 'Show more replies' button
                        continuations.append(next(search_dict(item, "buttonRenderer"))["command"])

            toolbar_payloads = search_dict(first_response, "engagementToolbarStateEntityPayload")
            toolbar_states = {payload["key"]: payload for payload in toolbar_payloads}
            for comment in reversed(list(search_dict(first_response, "commentEntityPayload"))):
                properties = comment["properties"]
                cid = properties["commentId"]
                author = comment["author"]
                toolbar = comment["toolbar"]
                toolbar_state = toolbar_states[properties["toolbarStateKey"]]
                text_content = properties["content"]["content"]
                result = {"cid": cid,
                          "text": text_content,
                          "text_length": len(text_content),
                          "time": properties["publishedTime"],
                          "author": author["displayName"],
                          "channel": author["channelId"],
                          "votes": toolbar["likeCountNotliked"].strip() or "0",
                          "replies": toolbar["replyCount"],
                          "photo": author["avatarThumbnailUrl"],
                          "heart": toolbar_state.get("heartState", "") == "TOOLBAR_HEART_STATE_HEARTED",
                          "reply": "." in cid}

                yield result
            time.sleep(sleep)

        while continuations:
            continuation = continuations.pop()
            response = self.ajax_request(continuation, ytcfg)

            if not response:
                break

            error = next(search_dict(response, "externalErrorMessage"), None)
            if error:
                raise RuntimeError("Error returned from server: " + error)

            actions = list(search_dict(response, "reloadContinuationItemsCommand")) + \
                      list(search_dict(response, "appendContinuationItemsAction"))
            for action in actions:
                for item in action.get("continuationItems", []):
                    if action["targetId"] in ["comments-section",
                                              "engagement-panel-comments-section",
                                              "shorts-engagement-panel-comments-section"]:
                        # Process continuations for comments and replies.
                        continuations[:0] = [ep for ep in search_dict(item, "continuationEndpoint")]
                    if action["targetId"].startswith("comment-replies-item") and "continuationItemRenderer" in item:
                        # Process the 'Show more replies' button
                        continuations.append(next(search_dict(item, "buttonRenderer"))["command"])

            toolbar_payloads = search_dict(response, "engagementToolbarStateEntityPayload")
            toolbar_states = {payload["key"]: payload for payload in toolbar_payloads}
            for comment in reversed(list(search_dict(response, "commentEntityPayload"))):
                properties = comment["properties"]
                cid = properties["commentId"]
                author = comment["author"]
                toolbar = comment["toolbar"]
                toolbar_state = toolbar_states[properties["toolbarStateKey"]]
                text_content = properties["content"]["content"]
                result = {"cid": cid,
                          "text": text_content,
                          "text_length": len(text_content),
                          "time": properties["publishedTime"],
                          "author": author["displayName"],
                          "channel": author["channelId"],
                          "votes": toolbar["likeCountNotliked"].strip() or "0",
                          "replies": toolbar["replyCount"],
                          "photo": author["avatarThumbnailUrl"],
                          "heart": toolbar_state.get("heartState", "") == "TOOLBAR_HEART_STATE_HEARTED",
                          "reply": "." in cid}

                yield result
            time.sleep(sleep)

    # NOTE: ytce.youtube.pagination.search_dict is used; do not re-implement here.
