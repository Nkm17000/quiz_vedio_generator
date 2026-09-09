def answer_html(q, index):
    from services.video_service import get_logo_base64

    question_data = q["question"]
    if isinstance(question_data, dict):
        question = (
            f'{question_data["en"]}'
            f'<br><span class="hi">{question_data["hi"]}</span>'
        )
        options = [
            f'{opt["en"]}<br><span class="hi-opt">{opt["hi"]}</span>'
            for opt in q["options"]
        ]
    else:
        question = question_data
        options = q["options"]

    option_html = "".join(
        f'<div class="option {"correct" if i == q["answer_index"] else ""}">'
        f'{chr(65 + i)}. {option}</div>'
        for i, option in enumerate(options)
    )

    explanation = q.get("explanation", "")
    if isinstance(explanation, dict):
        explanation_html = (
            f'<div class="explanation">💡 {explanation["en"]}'
            f'<span class="hi-exp">{explanation["hi"]}</span></div>'
        )
    elif explanation:
        explanation_html = f'<div class="explanation">💡 {explanation}</div>'
    else:
        explanation_html = ""

    logo_base64 = get_logo_base64()

    return f"""
<html>
<head>
<style>
body {{
    width: 1080px;
    height: 1920px;
    margin: 0;
    font-family: Arial, sans-serif;
    background: linear-gradient(180deg, #020d18, #0a2a43);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
}}
.container {{
    width: 90%;
    text-align: center;
}}
.logo {{
    width: 260px;
    height: 260px;
    border-radius: 50%;
    object-fit: cover;
    margin-bottom: 25px;
    box-shadow: 0 0 25px #00c3ff, 0 0 50px rgba(0,195,255,0.5);
    border: 4px solid rgba(255,255,255,0.2);
}}
.question {{
    font-size: 50px;
    margin-bottom: 40px;
    line-height: 1.4;
}}
.hi {{
    display: block;
    font-size: 30px;
    color: #cce6ff;
    margin-top: 10px;
}}
.option {{
    font-size: 36px;
    margin: 15px 0;
    padding: 20px;
    border-radius: 12px;
    background: rgba(255,255,255,0.1);
    border: 2px solid #00c3ff;
}}
.hi-opt {{
    display: block;
    font-size: 24px;
    color: #b3d9ff;
    margin-top: 5px;
}}
.correct {{
    background: #00ff9d;
    color: black;
    box-shadow: 0 0 20px #00ff9d;
    font-weight: bold;
}}
.explanation {{
    margin-top: 40px;
    padding: 25px;
    border-radius: 15px;
    border: 2px solid #ffcc00;
    background: rgba(255,204,0,0.1);
    font-size: 30px;
    color: #ffcc00;
    box-shadow: 0 0 15px rgba(255,204,0,0.5);
}}
.hi-exp {{
    display: block;
    font-size: 24px;
    color: #ffe599;
    margin-top: 10px;
}}
</style>
</head>
<body>
<div class="container">
    <img class="logo" src="data:image/png;base64,{logo_base64}" />
    <div class="question">Q{index + 1}. {question}</div>
    {option_html}
    {explanation_html}
</div>
</body>
</html>
"""
