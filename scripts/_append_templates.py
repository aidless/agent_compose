"""Append 15 new task templates (T11-T25) to task_templates.yaml.

Run once after Phase 4.1 to extend benchmark from 10 to 25 templates.
"""

from pathlib import Path

NEW_TEMPLATES = """\

  # ===== Phase 4 expanded templates (T11-T25) =====

  - id: T11_image_email
    description: "Classify an image and email the predicted label"
    natural_language: |
      Classify the image at {image_path} into one of {categories} and email
      the predicted label to {recipient_email}.
    required_tools: [image_classify, send_email]
    minimal_chain: [image_classify, send_email]
    extended_chain: [image_classify, summarize, send_email]
    parameters:
      image_path: ["/img/product_a.jpg", "/img/product_b.jpg", "/img/product_c.jpg"]
      categories: [["electronics", "clothing", "food"], ["car", "truck", "bike"]]
      recipient_email: ["alice@example.com", "bob@example.com"]
    success_criteria:
      - "send_email.to == {recipient_email}"

  - id: T12_ocr_write
    description: "Extract text from an image with OCR and write to a file"
    natural_language: |
      Run OCR on the image at {image_path} and write the extracted text to {output_file}.
    required_tools: [ocr_extract, write_file]
    minimal_chain: [ocr_extract, write_file]
    extended_chain: [ocr_extract, summarize, write_file]
    parameters:
      image_path: ["/img/receipt_a.jpg", "/img/receipt_b.jpg"]
      output_file: ["/tmp/receipt_a.txt", "/tmp/receipt_b.txt"]
    success_criteria:
      - "write_file.path == {output_file}"

  - id: T13_audio_translate
    description: "Transcribe audio, translate the text, send via Slack"
    natural_language: |
      Transcribe the audio at {audio_path}, translate the transcript to {target_language},
      and post the translation to Slack channel {channel}.
    required_tools: [audio_transcribe, translate, send_slack]
    minimal_chain: [audio_transcribe, translate, send_slack]
    extended_chain: [audio_transcribe, translate, summarize, send_slack]
    parameters:
      audio_path: ["/audio/announcement_a.mp3", "/audio/announcement_b.mp3"]
      target_language: ["fr", "es", "de", "ja"]
      channel: ["#general", "#translations", "#alerts"]
    success_criteria:
      - "send_slack.channel == {channel}"

  - id: T14_sql_filter_email
    description: "Query database, filter rows, email results"
    natural_language: |
      Query the {database} database with SQL: {sql_query}, then email the result rows
      to {recipient_email} as a summary.
    required_tools: [sql_query, summarize, send_email]
    minimal_chain: [sql_query, send_email]
    extended_chain: [sql_query, json_transform, summarize, send_email]
    parameters:
      database: ["main", "analytics", "archive"]
      sql_query: ["SELECT name FROM active_users", "SELECT id, email FROM customers LIMIT 5"]
      recipient_email: ["alice@example.com", "bob@example.com"]
    success_criteria:
      - "send_email.to == {recipient_email}"

  - id: T15_image_crop_ocr
    description: "Crop a region from an image, then OCR it"
    natural_language: |
      Crop a {width}x{height} region starting at ({x},{y}) from {source_path},
      then OCR the cropped region and save the text to {output_file}.
    required_tools: [image_crop, ocr_extract, write_file]
    minimal_chain: [image_crop, ocr_extract, write_file]
    extended_chain: [image_crop, ocr_extract, summarize, write_file]
    parameters:
      source_path: ["/img/page_a.jpg", "/img/page_b.jpg"]
      x: [50, 100, 150]
      y: [50, 100, 150]
      width: [200, 300]
      height: [100, 150]
      output_file: ["/tmp/cropped_a.txt", "/tmp/cropped_b.txt"]
    success_criteria:
      - "write_file.path == {output_file}"

  - id: T16_csv_aggregate_write
    description: "Filter CSV rows by condition and compute a statistic"
    natural_language: |
      Filter {csv_path} for rows where {column} {operator} {value}, compute the {stat}
      of the result, and append the value to {output_file}.
    required_tools: [csv_filter, statistics, append_file]
    minimal_chain: [csv_filter, statistics, append_file]
    extended_chain: [list_files, csv_filter, statistics, round, append_file]
    parameters:
      csv_path: ["/data/sales.csv", "/data/users.csv", "/data/events.csv"]
      column: ["amount", "age", "score", "duration"]
      operator: [">", "<", "==", "contains"]
      value: ["100", "30", "pass", "click"]
      stat: ["mean", "median", "max", "min"]
      output_file: ["/tmp/stats_a.txt", "/tmp/stats_b.txt"]
    success_criteria:
      - "append_file.path == {output_file}"

  - id: T17_translate_search_summary
    description: "Translate a query, search the web, summarize the results"
    natural_language: |
      Translate the query "{query}" from {source_lang} to English,
      search the web for the translated query, then summarize the top {max_results} results.
    required_tools: [translate, search_web, summarize]
    minimal_chain: [search_web, summarize]
    extended_chain: [translate, search_web, summarize]
    parameters:
      query: ["bonjour le monde", "konnichiwa", "tianqi yubao"]
      source_lang: ["fr", "ja", "zh"]
      max_results: [3, 5, 10]
    success_criteria:
      - "summarize called after search_web"

  - id: T18_datetime_format_calendar
    description: "Get current datetime, format it, create a calendar event"
    natural_language: |
      Get the current datetime, format it as {format}, and add a calendar event
      with title "{title}" starting at that time.
    required_tools: [get_datetime, format_date, calendar_add]
    minimal_chain: [get_datetime, format_date, calendar_add]
    extended_chain: [get_datetime, format_date, calendar_add, send_email]
    parameters:
      format: ["%Y-%m-%d", "%m/%d/%Y %H:%M", "%d %b %Y"]
      title: ["Standup", "Sprint Review", "Demo Day"]
    success_criteria:
      - "calendar_add.start_time matches formatted date"

  - id: T19_classify_image_save
    description: "Classify an image, save the label to a file, and email it"
    natural_language: |
      Classify the image at {image_path} into one of {categories}, save the label
      to {output_file}, and email a notification to {recipient_email}.
    required_tools: [image_classify, write_file, send_email]
    minimal_chain: [image_classify, write_file, send_email]
    extended_chain: [image_classify, write_file, send_email, send_slack]
    parameters:
      image_path: ["/img/scene_a.jpg", "/img/scene_b.jpg"]
      categories: [["indoor", "outdoor"], ["day", "night"], ["nature", "urban"]]
      output_file: ["/tmp/label_a.txt", "/tmp/label_b.txt"]
      recipient_email: ["alice@example.com", "bob@example.com"]
    success_criteria:
      - "write_file.path == {output_file}"
      - "send_email.to == {recipient_email}"

  - id: T20_audio_classify_notify
    description: "Classify an audio clip and notify if it matches a category"
    natural_language: |
      Classify the audio at {audio_path} into one of {categories}.
      If the label is {alert_label}, send a push notification to user {user_id}.
    required_tools: [audio_classify, send_push]
    minimal_chain: [audio_classify, send_push]
    extended_chain: [audio_classify, text_to_speech, send_push]
    parameters:
      audio_path: ["/audio/clip_a.mp3", "/audio/clip_b.mp3"]
      categories: [["speech", "music", "alarm", "silence"]]
      alert_label: ["alarm"]
      user_id: ["user_001", "user_002", "user_003"]
    success_criteria:
      - "if label == alert_label: send_push called"

  - id: T21_db_insert_email
    description: "Insert a row into a database and email a confirmation"
    natural_language: |
      Insert a new {record_type} record into {table} with values {values}, then email
      a confirmation to {recipient_email}.
    required_tools: [db_insert, send_email]
    minimal_chain: [db_insert, send_email]
    extended_chain: [db_insert, json_transform, summarize, send_email]
    parameters:
      record_type: ["user", "order", "event"]
      table: ["users", "orders", "events"]
      values: [{"name": "Alice", "active": 1}, {"order_id": "O123", "total": 99.99}]
      recipient_email: ["alice@example.com", "bob@example.com"]
    success_criteria:
      - "send_email.to == {recipient_email}"

  - id: T22_calendar_list_filter
    description: "List calendar events and filter by date range"
    natural_language: |
      List calendar events between {start_date} and {end_date}, then search for {keyword},
      and email the count to {recipient_email}.
    required_tools: [calendar_list, search_web, send_email]
    minimal_chain: [calendar_list, search_web, send_email]
    extended_chain: [calendar_list, search_web, send_email, send_slack]
    parameters:
      start_date: ["2026-08-01", "2026-09-01"]
      end_date: ["2026-08-31", "2026-09-30"]
      keyword: ["meeting", "review", "demo"]
      recipient_email: ["alice@example.com", "bob@example.com"]
    success_criteria:
      - "send_email.to == {recipient_email}"

  - id: T23_transcribe_translate_write
    description: "Transcribe audio, translate the transcript, and write to file"
    natural_language: |
      Transcribe the audio at {audio_path}, translate the result to {target_language},
      and write the translation to {output_file}.
    required_tools: [audio_transcribe, translate, write_file]
    minimal_chain: [audio_transcribe, translate, write_file]
    extended_chain: [audio_transcribe, translate, summarize, write_file]
    parameters:
      audio_path: ["/audio/speech_a.mp3", "/audio/speech_b.mp3"]
      target_language: ["en", "es", "zh", "fr"]
      output_file: ["/tmp/transcript_a.txt", "/tmp/transcript_b.txt"]
    success_criteria:
      - "write_file.path == {output_file}"

  - id: T24_image_search_summary
    description: "Search for images, resize one, and email a summary"
    natural_language: |
      Search for images matching {query}, resize the first result to {width}x{height},
      and email a summary to {recipient_email}.
    required_tools: [search_image, image_resize, send_email]
    minimal_chain: [search_image, image_resize, send_email]
    extended_chain: [search_image, image_resize, summarize, send_email]
    parameters:
      query: ["Tokyo skyline", "Eiffel Tower", "New York city"]
      width: [800, 1024, 1280]
      height: [600, 768, 720]
      recipient_email: ["alice@example.com", "bob@example.com"]
    success_criteria:
      - "send_email.to == {recipient_email}"

  - id: T25_json_transform_stats
    description: "Transform a JSON object, compute a statistic, and append to a file"
    natural_language: |
      Take the JSON object {input_json}, pick keys {pick_keys}, compute the {stat}
      statistic over the numeric values, and append the result to {output_file}.
    required_tools: [json_transform, statistics, append_file]
    minimal_chain: [json_transform, statistics, append_file]
    extended_chain: [json_transform, statistics, round, append_file]
    parameters:
      input_json: [{"a": 1, "b": 2, "c": 3, "x": "ignore"}, {"score": 80, "time": 42, "label": "ok"}]
      pick_keys: [["a", "b", "c"], ["score", "time"]]
      stat: ["mean", "sum", "max"]
      output_file: ["/tmp/json_stats_a.txt", "/tmp/json_stats_b.txt"]
    success_criteria:
      - "append_file.path == {output_file}"
"""


def main() -> None:
    path = Path(__file__).parent.parent / "templates" / "task_templates.yaml"
    existing = path.read_text(encoding="utf-8")
    # Idempotency: skip if already appended
    if "T11_image_email" in existing:
        print("T11-T25 already present; skipping.")
        return
    path.write_text(existing.rstrip("\n") + "\n" + NEW_TEMPLATES, encoding="utf-8")
    print(f"Appended 15 templates to {path}")


if __name__ == "__main__":
    main()
