# -*- coding: utf-8 -*-
"""Hebrew names for the data source's English industry and country labels. A label
missing here is not shown, rather than shown in English inside a Hebrew screen."""

INDUSTRY = {
    "Advertising Agencies": "פרסום ושיווק", "Aerospace & Defense": "תעופה וביטחון",
    "Agricultural Inputs": "תשומות חקלאיות", "Airlines": "תעופה אזרחית",
    "Apparel Manufacturing": "ייצור הלבשה", "Apparel Retail": "קמעונאות הלבשה",
    "Asset Management": "ניהול נכסים", "Auto & Truck Dealerships": "סוכנויות רכב",
    "Auto Manufacturers": "יצרניות רכב", "Auto Parts": "חלקי רכב",
    "Banks - Diversified": "בנקים גדולים", "Banks - Regional": "בנקים אזוריים",
    "Beverages - Brewers": "בירה", "Beverages - Non-Alcoholic": "משקאות קלים",
    "Beverages - Wineries & Distilleries": "יין ומשקאות חריפים", "Biotechnology": "ביוטכנולוגיה",
    "Building Materials": "חומרי בניין", "Building Products & Equipment": "מוצרי בנייה וציוד",
    "Capital Markets": "שוק ההון", "Chemicals": "כימיקלים",
    "Communication Equipment": "ציוד תקשורת", "Computer Hardware": "חומרת מחשבים",
    "Confectioners": "ממתקים", "Conglomerates": "קונגלומרטים",
    "Consulting Services": "שירותי ייעוץ", "Consumer Electronics": "מוצרי אלקטרוניקה לצרכן",
    "Copper": "נחושת", "Credit Services": "שירותי אשראי ותשלומים",
    "Diagnostics & Research": "אבחון ומחקר רפואי", "Discount Stores": "רשתות הנחות",
    "Drug Manufacturers - General": "יצרניות תרופות", "Drug Manufacturers - Specialty & Generic": "תרופות ייעודיות וגנריות",
    "Electrical Equipment & Parts": "ציוד חשמלי", "Electronic Components": "רכיבים אלקטרוניים",
    "Electronic Gaming & Multimedia": "משחקי מחשב ומולטימדיה", "Engineering & Construction": "הנדסה ובנייה",
    "Entertainment": "בידור ומדיה", "Farm & Heavy Construction Machinery": "מכונות חקלאיות וכבדות",
    "Farm Products": "מוצרי חקלאות", "Financial Data & Stock Exchanges": "בורסות ומידע פיננסי",
    "Food Distribution": "הפצת מזון", "Footwear & Accessories": "הנעלה ואביזרים",
    "Gold": "זהב", "Grocery Stores": "רשתות מזון",
    "Health Information Services": "מערכות מידע לבריאות", "Healthcare Plans": "ביטוח בריאות",
    "Home Improvement Retail": "רשתות לבית ולשיפוצים", "Household & Personal Products": "מוצרי צריכה לבית",
    "Industrial Distribution": "הפצה תעשייתית", "Information Technology Services": "שירותי מחשוב",
    "Insurance - Diversified": "ביטוח", "Insurance - Life": "ביטוח חיים",
    "Insurance - Property & Casualty": "ביטוח כללי", "Insurance - Reinsurance": "ביטוח משנה",
    "Insurance Brokers": "סוכנות ביטוח", "Integrated Freight & Logistics": "לוגיסטיקה ושילוח",
    "Internet Content & Information": "תוכן ושירותי אינטרנט", "Internet Retail": "מסחר מקוון",
    "Leisure": "פנאי", "Lodging": "מלונאות", "Luxury Goods": "מוצרי יוקרה",
    "Medical Care Facilities": "מוסדות רפואיים", "Medical Devices": "מכשור רפואי",
    "Medical Distribution": "הפצה רפואית", "Medical Instruments & Supplies": "ציוד ואספקה רפואית",
    "Oil & Gas E&P": "חיפוש והפקת נפט וגז", "Oil & Gas Equipment & Services": "ציוד ושירותים לנפט וגז",
    "Oil & Gas Integrated": "נפט וגז משולבת", "Oil & Gas Midstream": "הובלה ואחסון נפט וגז",
    "Oil & Gas Refining & Marketing": "זיקוק ושיווק דלק", "Packaged Foods": "מזון ארוז",
    "Packaging & Containers": "אריזות ומכלים", "Personal Services": "שירותים אישיים",
    "Pollution & Treatment Controls": "טיפול בזיהום", "REIT - Diversified": "קרן נדל״ן מגוונת",
    "REIT - Healthcare Facilities": "קרן נדל״ן למבני בריאות", "REIT - Hotel & Motel": "קרן נדל״ן למלונות",
    "REIT - Industrial": "קרן נדל״ן תעשייתי", "REIT - Office": "קרן נדל״ן משרדים",
    "REIT - Residential": "קרן נדל״ן למגורים", "REIT - Retail": "קרן נדל״ן מסחרי",
    "REIT - Specialty": "קרן נדל״ן ייעודית", "Railroads": "רכבות משא",
    "Real Estate Services": "שירותי נדל״ן", "Rental & Leasing Services": "השכרה וליסינג",
    "Residential Construction": "בנייה למגורים", "Resorts & Casinos": "אתרי נופש וקזינו",
    "Restaurants": "מסעדות", "Scientific & Technical Instruments": "מכשור מדעי וטכני",
    "Security & Protection Services": "שירותי אבטחה", "Semiconductor Equipment & Materials": "ציוד וחומרים לשבבים",
    "Semiconductors": "שבבים", "Software - Application": "תוכנה יישומית",
    "Software - Infrastructure": "תוכנת תשתית", "Solar": "אנרגיה סולארית",
    "Specialty Business Services": "שירותים עסקיים", "Specialty Chemicals": "כימיקלים מיוחדים",
    "Specialty Industrial Machinery": "מכונות תעשייתיות", "Specialty Retail": "קמעונאות ייעודית",
    "Steel": "פלדה", "Telecom Services": "שירותי תקשורת", "Tobacco": "טבק",
    "Tools & Accessories": "כלי עבודה", "Travel Services": "שירותי תיירות", "Trucking": "הובלה יבשתית",
    "Utilities - Diversified": "תשתיות חשמל וגז", "Utilities - Independent Power Producers": "יצרני חשמל פרטיים",
    "Utilities - Regulated Electric": "חברת חשמל", "Utilities - Regulated Gas": "חברת גז",
    "Utilities - Regulated Water": "חברת מים", "Waste Management": "טיפול בפסולת",
}

COUNTRY = {
    "United States": "ארצות הברית", "Ireland": "אירלנד", "United Kingdom": "בריטניה",
    "Switzerland": "שווייץ", "Netherlands": "הולנד", "Canada": "קנדה", "Bermuda": "ברמודה",
    "Israel": "ישראל", "Germany": "גרמניה", "France": "צרפת", "Jersey": "ג׳רזי",
    "Luxembourg": "לוקסמבורג", "Singapore": "סינגפור", "Japan": "יפן", "China": "סין",
    "Taiwan": "טייוואן", "Netherlands Antilles": "האנטילים ההולנדיים", "Uruguay": "אורוגוואי",
}


def industry(x):
    return INDUSTRY.get(x) if x else None


def country(x):
    return COUNTRY.get(x) if x else None
