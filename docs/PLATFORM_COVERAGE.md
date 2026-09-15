# Platform coverage and prioritisation

The canonical machine-readable list is `config/surfaces.yaml`. This document explains how to use it.

## Core global

ChatGPT, Gemini, Google AI Mode, Google AI Overviews, Microsoft Copilot, Bing Copilot Search, Claude, Perplexity, DeepSeek Chat, Grok and Meta AI must always appear in the observation plane.

## China

Doubao, Qwen, Quark AI, Tencent Yuanbao, Kimi, Baidu AI Search, Baidu Wenxin Assistant, 360 Nano AI Search and Zhipu Qingyan are first-class surfaces. DeepSeek is treated as both global and China-relevant. China-specific audience evidence must not be replaced by Western web-traffic proxies.

## Regional

NAVER AI search and Kakao Kanana (Korea), Yandex Search/Alice (Russia/CIS) and GigaChat (Russia/CIS) are first-class regional surfaces because regional scale can be commercially significant even when global-share dashboards understate them.

## Secondary/watchlist

Le Chat, You.com, Duck.ai, Brave AI/Leo, Genspark, Felo, Manus, Poe, Apple Intelligence/Siri and Amazon Rufus remain visible in the registry. Their priority can rise when reach, commercial intent or market relevance crosses the significance threshold.

## Separate surface, model and distribution

Never treat a model family as a discovery channel. For example, a related model may power an API, a consumer chat interface, a search augmentation layer and a commerce experience with different retrieval/citation behaviour. Store each consumer surface separately and link them by family/vendor.

## Unknowns

`retrieval_status: under_documented` is useful product data. The UI should make unknown retrieval architecture, missing regional usage evidence and stale evidence obvious rather than silently dropping the row.
