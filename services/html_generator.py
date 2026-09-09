def create_html(q, index, timer=3):
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
    display: flex;
    justify-content: center;
    align-items: center;
    color: white;
}}
.container {{
    width: 90%;
    text-align: center;
}}
.logo {{
    width: 240px;
    height: 240px;
    border-radius: 50%;
    object-fit: cover;
    margin-bottom: 20px;
    box-shadow: 0 0 25px #00c3ff, 0 0 50px rgba(0,195,255,0.5);
    border: 4px solid rgba(255,255,255,0.2);
}}
.timer {{
    font-size: 75px;
    color: #ffcc00;
    margin-bottom: 20px;
    font-weight: bold;
}}
.question {{
    font-size: 46px;
    margin: 30px 0;
    line-height: 1.4;
}}
.hi {{
    display: block;
    font-size: 30px;
    color: #cce6ff;
    margin-top: 10px;
}}
.option {{
    margin: 18px 0;
    padding: 22px;
    border-radius: 18px;
    border: 2px solid #00c3ff;
    font-size: 32px;
    background: rgba(255,255,255,0.05);
}}
.hi-opt {{
    display: block;
    font-size: 22px;
    color: #b3d9ff;
    margin-top: 5px;
}}
.footer {{
    margin-top: 40px;
    font-size: 28px;
    color: #00ff9d;
    text-shadow: 0 0 10px #00ff9d;
}}
</style>
</head>
<body>
<div class="container">
    <img src="data:image/png;base64,{logo_base64}" class="logo"/>
    <div class="timer">⏳ {timer}</div>
    <div class="question">Q{index + 1}. {question}</div>
    <div class="option">A. {options[0]}</div>
    <div class="option">B. {options[1]}</div>
    <div class="option">C. {options[2]}</div>
    <div class="option">D. {options[3]}</div>
    <div class="footer">🔥 Comment your answer!</div>
</div>
</body>
</html>
"""
