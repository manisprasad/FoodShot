import base64
from pathlib import Path

# Path to the source logo image
img_path = Path("/Users/soroqn/Documents/2026-08-09 4.11.31 PM.jpg")

with open(img_path, "rb") as f:
    b64_data = base64.b64encode(f.read()).decode("utf-8")

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 640" width="1280" height="640">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&amp;display=swap');
      text {{ font-family: 'Outfit', system-ui, sans-serif; }}
    </style>
    <clipPath id="logo-clip">
      <circle cx="340" cy="270" r="120" />
    </clipPath>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="15" flood-color="#000000" flood-opacity="0.06" />
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1280" height="640" fill="#FDFBF7" rx="20" ry="20" />
  
  <!-- Subtle Dot Grid Background -->
  <pattern id="dots" x="0" y="0" width="30" height="30" patternUnits="userSpaceOnUse">
    <circle fill="#EBE5D9" cx="15" cy="15" r="1.5"></circle>
  </pattern>
  <rect x="0" y="0" width="1280" height="640" fill="url(#dots)" rx="20" ry="20"/>

  <!-- Left Side: Logo and Title -->
  <g transform="translate(0, -20)">
    <!-- Logo with shadow -->
    <circle cx="340" cy="270" r="120" fill="#ffffff" filter="url(#shadow)" />
    <image href="data:image/jpeg;base64,{b64_data}" x="220" y="150" width="240" height="240" clip-path="url(#logo-clip)" />
    
    <text x="340" y="470" font-size="72" font-weight="700" fill="#3A3A3A" text-anchor="middle" letter-spacing="-1">FoodShot</text>
    <text x="340" y="525" font-size="32" font-weight="600" fill="#888888" text-anchor="middle">Snap. Count.</text>
  </g>

  <!-- Right Side: Features -->
  <g transform="translate(70, 0)">
    
    <!-- Circles Base (Filled with background color and shadow to overlay each other) -->
    <!-- Top Circle Base -->
    <circle cx="820" cy="240" r="120" fill="#FDFBF7" filter="url(#shadow)"/>
    <!-- Bottom Left Circle Base -->
    <circle cx="720" cy="410" r="120" fill="#FDFBF7" filter="url(#shadow)"/>
    <!-- Bottom Right Circle Base -->
    <circle cx="920" cy="410" r="120" fill="#FDFBF7" filter="url(#shadow)"/>

    <!-- Top Circle Content (AI Vision) -->
    <circle cx="820" cy="240" r="104" fill="none" stroke="#F8B083" stroke-width="28" stroke-opacity="0.9"/>
    <text x="820" y="235" font-size="28" font-weight="700" fill="#4A4A4A" text-anchor="middle">AI Vision</text>
    <text x="820" y="270" font-size="18" font-weight="600" fill="#999999" text-anchor="middle">GPT-4o</text>

    <!-- Bottom Left Circle Content (Nutrition) -->
    <circle cx="720" cy="410" r="104" fill="none" stroke="#A7D5AF" stroke-width="28" stroke-opacity="0.9"/>
    <text x="720" y="405" font-size="28" font-weight="700" fill="#4A4A4A" text-anchor="middle">Nutrition</text>
    <text x="720" y="440" font-size="18" font-weight="600" fill="#999999" text-anchor="middle">USDA Data</text>

    <!-- Bottom Right Circle Content (Diabetes) -->
    <circle cx="920" cy="410" r="104" fill="none" stroke="#FDE08B" stroke-width="28" stroke-opacity="0.9"/>
    <text x="920" y="405" font-size="28" font-weight="700" fill="#4A4A4A" text-anchor="middle">Diabetes</text>
    <text x="920" y="440" font-size="18" font-weight="600" fill="#999999" text-anchor="middle">Insulin Calc</text>

  </g>
</svg>
"""

out_path = Path("docs/banner.svg")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(svg_content)
    
print(f"Generated SVG at {out_path}")
