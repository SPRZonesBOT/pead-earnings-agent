def fetch_bse_via_api() -> List[Dict]:
    raw_data = []
    try:
        response = requests.get(BSE_API_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()

        # Debug: Check what we actually got
        content_type = response.headers.get("Content-Type", "")
        logger.debug(f"BSE API response type: {content_type}")

        # Try to parse as JSON
        try:
            data = response.json()
        except ValueError:
            logger.warning("BSE API returned non-JSON response. Trying alternative format...")
            # Sometimes BSE returns wrapped JSON in HTML, try extracting it
            text = response.text
            if "<" in text and ">" in text:
                logger.debug("Response appears to be HTML, skipping BSE API.")
                return []
            # If it's just a string, try parsing it as JSON anyway
            try:
                data = eval(text)  # Not safe, but BSE sometimes does this
            except:
                logger.error(f"Could not parse BSE API response as JSON or Python.")
                return []

        # Handle response format
        if isinstance(data, str):
            logger.error(f"BSE API returned string instead of dict/list. Content: {data[:100]}")
            return []

        if isinstance(data, dict):
            items = data.get("Table", data.get("data", []))
        elif isinstance(data, list):
            items = data
        else:
            logger.error(f"Unexpected BSE API response format: {type(data)}")
            return []

        if not items:
            logger.info("BSE API returned empty results.")
            return []

        for item in items[:50]:
            if not isinstance(item, dict):
                continue

            attachment = str(item.get("ATTACHMENTNAME", item.get("attachment", ""))).strip()
            pdf_url = ""
            if attachment:
                pdf_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment}"

            raw_data.append({
                "date":    str(item.get("NEWS_DT", item.get("date", "")))[:10],
                "company": str(item.get("SLONGNAME", item.get("companyName", "N/A"))).strip(),
                "subject": str(item.get("NEWSSUB", item.get("subject", "N/A"))).strip(),
                "symbol":  str(item.get("SCRIP_CD", item.get("symbol", "N/A"))).strip(),
                "pdf_url": pdf_url,
                "source":  "BSE"
            })

        logger.info(f"BSE API: Successfully parsed {len(raw_data)} items.")

    except requests.exceptions.HTTPError as e:
        logger.error(f"BSE API HTTP error: {e}")
    except requests.exceptions.Timeout:
        logger.error("BSE API timed out.")
    except requests.exceptions.ConnectionError:
        logger.error("BSE API connection error.")
    except Exception as e:
        logger.error(f"BSE API unexpected error: {e}", exc_info=False)

    return raw_data
