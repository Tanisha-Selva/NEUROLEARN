"""
backend.py — NeuroLearnAI v2
Core evaluation engine.

Provides:
  - SUBJECTS         : Available subjects/topics per role
  - QUESTION_BANK    : ~8 questions per topic (School + College)
  - get_question_set : Random sample of N questions for a topic
  - evaluate_performance : Full adaptive evaluation pipeline
  - extract_pdf_text : Extract text from uploaded PDF (PyPDF2)
  - analyze_pdf_content : Keyword-based topic analysis of PDF text
"""

import json
import os
import random
from typing import Any, Dict, List, Optional

from ai_engine import generate_feedback
from adaptive import get_difficulty, get_difficulty_summary, get_next_difficulty
from db import save_result

# ── Resource map ────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))
_RESOURCES_PATH = os.path.join(_BASE, "resources.json")

try:
    with open(_RESOURCES_PATH, "r", encoding="utf-8") as _f:
        _RESOURCES: Dict = json.load(_f)
except Exception as _e:
    print(f"[BACKEND WARNING] Could not load resources.json: {_e}")
    _RESOURCES = {}

# ── Subject catalogue ───────────────────────────────────────────────────────────
SUBJECTS: Dict[str, Dict[str, List[str]]] = {
    "School": {
        "Math"       : ["Algebra", "Geometry", "Arithmetic"],
        "Physics"    : ["Motion", "Forces", "Light & Sound"],
        "Chemistry"  : ["Atoms & Molecules", "Chemical Reactions"],
        "Biology"    : ["Cells", "Ecology", "Human Body"],
        "History"    : ["Ancient History", "Modern History", "World Wars"],
        "Geography"  : ["Maps & Coordinates", "Climate & Weather"],
    },
    "College": {
        "Programming" : ["Arrays", "Loops", "Pointers", "Functions", "Recursion"],
        "Mathematics" : ["Calculus", "Linear Algebra", "Statistics", "Discrete Math"],
        "CS Core"     : ["Data Structures", "Algorithms", "Operating Systems", "DBMS"],
        "Machine Learning": ["Supervised Learning", "Unsupervised Learning", "Neural Networks"],
    },
}

# ── Question bank ───────────────────────────────────────────────────────────────
# Format: {"q": str, "opts": [A,B,C,D], "ans": str (exact match to one opt)}
QUESTION_BANK: Dict[str, Dict[str, Dict[str, List[Dict]]]] = {

    "School": {

        "Math": {
            "Algebra": [
                {"q": "Solve: 3x + 6 = 21",                    "opts": ["x=3","x=4","x=5","x=6"],         "ans": "x=5"},
                {"q": "If 2x − 4 = 10, then x = ?",            "opts": ["5","6","7","8"],                  "ans": "7"},
                {"q": "What is the slope of y = 4x − 3?",      "opts": ["−3","3","4","7"],                 "ans": "4"},
                {"q": "Expand: (x + 3)(x − 2)",                "opts": ["x²+x−6","x²−x−6","x²+x+6","x²−5x−6"], "ans": "x²+x−6"},
                {"q": "If x² = 64, then x = ? (positive)",     "opts": ["6","7","8","9"],                  "ans": "8"},
                {"q": "Simplify: 5x + 2x − 3x",                "opts": ["3x","4x","5x","6x"],              "ans": "4x"},
                {"q": "Which is a quadratic equation?",         "opts": ["2x+3=0","x³=8","x²+2x=0","√x=4"],"ans": "x²+2x=0"},
                {"q": "Factorize: x² − 9",                     "opts": ["(x−3)(x+3)","(x−9)(x+1)","(x+3)²","(x−3)²"], "ans": "(x−3)(x+3)"},
            ],
            "Geometry": [
                {"q": "Sum of angles in a triangle?",           "opts": ["90°","180°","270°","360°"],       "ans": "180°"},
                {"q": "Area of circle with radius 7 (π=22/7)?","opts": ["144","154","164","174"],           "ans": "154"},
                {"q": "Perimeter of a square with side 6 cm?", "opts": ["18 cm","20 cm","24 cm","36 cm"],  "ans": "24 cm"},
                {"q": "How many sides does a hexagon have?",    "opts": ["5","6","7","8"],                  "ans": "6"},
                {"q": "Area of rectangle: length=8, width=5?", "opts": ["30","35","40","45"],              "ans": "40"},
                {"q": "Volume of a cube with side 3?",          "opts": ["9","18","27","36"],               "ans": "27"},
                {"q": "The longest side of a right triangle?",  "opts": ["Base","Height","Hypotenuse","Perpendicular"], "ans": "Hypotenuse"},
                {"q": "Complementary angles add up to?",        "opts": ["90°","180°","270°","360°"],       "ans": "90°"},
            ],
            "Arithmetic": [
                {"q": "LCM of 4 and 6?",                        "opts": ["8","10","12","24"],               "ans": "12"},
                {"q": "HCF of 12 and 18?",                      "opts": ["3","4","6","9"],                  "ans": "6"},
                {"q": "15% of 200 = ?",                         "opts": ["25","30","35","40"],              "ans": "30"},
                {"q": "3/4 + 1/4 = ?",                          "opts": ["4/8","1","4/5","3/8"],            "ans": "1"},
                {"q": "√144 = ?",                               "opts": ["10","11","12","13"],              "ans": "12"},
                {"q": "2⁴ = ?",                                 "opts": ["8","12","16","32"],               "ans": "16"},
                {"q": "1001 − 598 = ?",                         "opts": ["393","403","413","423"],          "ans": "403"},
                {"q": "Average of 10, 20, 30 = ?",              "opts": ["15","20","25","30"],              "ans": "20"},
            ],
        },

        "Physics": {
            "Motion": [
                {"q": "Speed = Distance / ?",                   "opts": ["Mass","Time","Force","Area"],     "ans": "Time"},
                {"q": "SI unit of velocity?",                   "opts": ["km/h","m/s²","m/s","cm/s"],      "ans": "m/s"},
                {"q": "If d = 100 m and t = 5 s, speed = ?",   "opts": ["10 m/s","15 m/s","20 m/s","25 m/s"], "ans": "20 m/s"},
                {"q": "A body at rest has velocity = ?",        "opts": ["1 m/s","10 m/s","0 m/s","Infinite"], "ans": "0 m/s"},
                {"q": "Acceleration is change in velocity / ?", "opts": ["Distance","Time","Force","Mass"], "ans": "Time"},
                {"q": "Uniform motion means speed is ?",        "opts": ["Increasing","Decreasing","Constant","Zero"], "ans": "Constant"},
                {"q": "Distance is a ___ quantity.",            "opts": ["vector","scalar","derived","fundamental"], "ans": "scalar"},
                {"q": "Displacement considers ___ only.",       "opts": ["path length","speed","shortest route","time"], "ans": "shortest route"},
            ],
            "Forces": [
                {"q": "Newton's 2nd Law: F = ?",                "opts": ["mv","ma","mg","m/a"],             "ans": "ma"},
                {"q": "SI unit of force?",                      "opts": ["Joule","Watt","Newton","Pascal"], "ans": "Newton"},
                {"q": "Friction acts ___ to motion.",           "opts": ["parallel","opposite","perpendicular","along"], "ans": "opposite"},
                {"q": "Weight = mass × ?",                      "opts": ["velocity","acceleration","g","density"], "ans": "g"},
                {"q": "Newton's 3rd law is about?",             "opts": ["inertia","action-reaction","gravity","friction"], "ans": "action-reaction"},
                {"q": "A body moving in a circle experiences?", "opts": ["centrifugal force","centripetal force","gravity only","no force"], "ans": "centripetal force"},
                {"q": "Mass is measured in?",                   "opts": ["Newton","Kg","metre","joule"],    "ans": "Kg"},
                {"q": "Gravity on Earth is approximately?",     "opts": ["9.8 m/s²","6.7 m/s²","10.8 m/s²","8.9 m/s²"], "ans": "9.8 m/s²"},
            ],
            "Light & Sound": [
                {"q": "Speed of light in vacuum?",              "opts": ["3×10⁸ m/s","3×10⁶ m/s","3×10¹⁰ m/s","3×10⁴ m/s"], "ans": "3×10⁸ m/s"},
                {"q": "Sound travels fastest in?",              "opts": ["vacuum","water","air","solid"],   "ans": "solid"},
                {"q": "Reflection law: angle of incidence = ?", "opts": ["angle of refraction","angle of reflection","90°","0°"], "ans": "angle of reflection"},
                {"q": "Unit of sound intensity?",               "opts": ["Hz","Watt","Decibel","Pascal"],   "ans": "Decibel"},
                {"q": "Frequency of sound is measured in?",     "opts": ["Decibel","Hertz","Metre","Newton"], "ans": "Hertz"},
                {"q": "Concave mirror is ___ mirror.",          "opts": ["diverging","converging","plane","flat"], "ans": "converging"},
                {"q": "Sound cannot travel through?",           "opts": ["water","air","glass","vacuum"],   "ans": "vacuum"},
                {"q": "Pitch of sound depends on?",             "opts": ["amplitude","frequency","speed","wavelength"], "ans": "frequency"},
            ],
        },

        "Chemistry": {
            "Atoms & Molecules": [
                {"q": "Protons are found in the ___ of an atom.", "opts": ["orbit","shell","nucleus","cloud"], "ans": "nucleus"},
                {"q": "Atomic number is the count of?",         "opts": ["neutrons","protons","electrons","nucleons"], "ans": "protons"},
                {"q": "Mass number = protons + ?",              "opts": ["electrons","protons","neutrons","isotopes"], "ans": "neutrons"},
                {"q": "Chemical symbol for Gold?",              "opts": ["Go","Gd","Au","Ag"],               "ans": "Au"},
                {"q": "Valency of Carbon?",                     "opts": ["2","3","4","6"],                  "ans": "4"},
                {"q": "Isotopes have the same number of?",      "opts": ["neutrons","protons","mass numbers","electrons"], "ans": "protons"},
                {"q": "What carries a negative charge?",        "opts": ["proton","neutron","electron","nucleus"], "ans": "electron"},
                {"q": "Molecular formula of water?",            "opts": ["HO","H₂O","H₂O₂","OH"],          "ans": "H₂O"},
            ],
            "Chemical Reactions": [
                {"q": "Rusting of iron is a ___ reaction.",     "opts": ["decomposition","oxidation","displacement","combination"], "ans": "oxidation"},
                {"q": "pH of pure water?",                      "opts": ["5","6","7","8"],                  "ans": "7"},
                {"q": "Acid + Base → ?",                        "opts": ["acid + water","salt + water","base + gas","gas + water"], "ans": "salt + water"},
                {"q": "Which gas is produced when acid reacts with metal?", "opts": ["O₂","CO₂","H₂","N₂"], "ans": "H₂"},
                {"q": "CaCO₃ → CaO + CO₂ is?",                "opts": ["combination","decomposition","displacement","redox"], "ans": "decomposition"},
                {"q": "Photosynthesis is an example of?",       "opts": ["exothermic","endothermic","acid-base","physical"], "ans": "endothermic"},
                {"q": "NaOH is an example of?",                 "opts": ["acid","salt","base","indicator"],  "ans": "base"},
                {"q": "Which is a physical change?",            "opts": ["burning","rusting","melting ice","cooking"], "ans": "melting ice"},
            ],
        },

        "Biology": {
            "Cells": [
                {"q": "Powerhouse of the cell?",                "opts": ["Ribosome","Nucleus","Mitochondria","Chloroplast"], "ans": "Mitochondria"},
                {"q": "Cell wall is found in ___ cells.",       "opts": ["animal","fungal","plant","bacterial,plant and fungal"], "ans": "bacterial,plant and fungal"},
                {"q": "DNA is found in the?",                   "opts": ["cytoplasm","cell wall","nucleus","ribosome"], "ans": "nucleus"},
                {"q": "Smallest unit of life?",                 "opts": ["tissue","organ","cell","molecule"], "ans": "cell"},
                {"q": "Photosynthesis occurs in the?",          "opts": ["nucleus","ribosome","mitochondria","chloroplast"], "ans": "chloroplast"},
                {"q": "Cell membrane is made of?",              "opts": ["cellulose","lipids and proteins","starch","DNA"], "ans": "lipids and proteins"},
                {"q": "Ribosomes are responsible for?",         "opts": ["energy production","protein synthesis","digestion","cell division"], "ans": "protein synthesis"},
                {"q": "Which organelle packages proteins?",     "opts": ["mitochondria","nucleus","golgi apparatus","ribosome"], "ans": "golgi apparatus"},
            ],
            "Ecology": [
                {"q": "First trophic level contains?",          "opts": ["consumers","decomposers","producers","predators"], "ans": "producers"},
                {"q": "Decomposers break down?",                "opts": ["sunlight","dead organic matter","CO₂","water"], "ans": "dead organic matter"},
                {"q": "Ozone layer protects against?",          "opts": ["acid rain","UV radiation","noise pollution","global warming"], "ans": "UV radiation"},
                {"q": "Organisms that make their own food?",    "opts": ["heterotrophs","parasites","autotrophs","omnivores"], "ans": "autotrophs"},
                {"q": "A food chain starts with?",              "opts": ["carnivore","decomposer","producer","herbivore"], "ans": "producer"},
                {"q": "Greenhouse gases include?",              "opts": ["N₂","O₂","CO₂","H₂"],             "ans": "CO₂"},
                {"q": "Biodiversity means variety of?",         "opts": ["rocks","species","gases","water"],  "ans": "species"},
                {"q": "Which is a renewable resource?",         "opts": ["coal","petrol","solar energy","natural gas"], "ans": "solar energy"},
            ],
            "Human Body": [
                {"q": "How many chambers does the human heart have?", "opts": ["2","3","4","6"],             "ans": "4"},
                {"q": "Bones meet at a?",                       "opts": ["tendon","ligament","joint","muscle"], "ans": "joint"},
                {"q": "Largest organ of the human body?",       "opts": ["liver","brain","lungs","skin"],   "ans": "skin"},
                {"q": "Insulin is produced by the?",            "opts": ["liver","pancreas","kidney","heart"], "ans": "pancreas"},
                {"q": "Blood type that is universal donor?",    "opts": ["A","B","AB","O"],                 "ans": "O"},
                {"q": "Which system controls body coordination?","opts": ["digestive","nervous","respiratory","excretory"], "ans": "nervous"},
                {"q": "Lungs are part of the ___ system.",      "opts": ["digestive","circulatory","respiratory","excretory"], "ans": "respiratory"},
                {"q": "Kidneys filter?",                        "opts": ["air","blood","food","lymph"],      "ans": "blood"},
            ],
        },

        "History": {
            "Ancient History": [
                {"q": "Indus Valley Civilization was around?",  "opts": ["1000 BCE","2500 BCE","500 BCE","3500 BCE"], "ans": "2500 BCE"},
                {"q": "Ancient Olympics originated in?",        "opts": ["Rome","Egypt","Greece","Persia"],  "ans": "Greece"},
                {"q": "Pyramids were built by?",                "opts": ["Greeks","Romans","Ancient Egyptians","Mesopotamians"], "ans": "Ancient Egyptians"},
                {"q": "First emperor of China?",                "opts": ["Confucius","Qin Shi Huang","Genghis Khan","Kublai Khan"], "ans": "Qin Shi Huang"},
                {"q": "The Colosseum is located in?",           "opts": ["Greece","Egypt","Rome","Carthage"], "ans": "Rome"},
                {"q": "Mesopotamia was in modern-day?",         "opts": ["Egypt","Iran","Iraq","Turkey"],    "ans": "Iraq"},
                {"q": "Who wrote the Iliad?",                   "opts": ["Socrates","Plato","Homer","Aristotle"], "ans": "Homer"},
                {"q": "Ashoka the Great belonged to which dynasty?", "opts": ["Gupta","Maurya","Mughal","Chola"], "ans": "Maurya"},
            ],
            "Modern History": [
                {"q": "Industrial Revolution started in?",      "opts": ["France","Germany","England","USA"], "ans": "England"},
                {"q": "French Revolution year?",                "opts": ["1689","1776","1789","1848"],       "ans": "1789"},
                {"q": "UN was established in?",                 "opts": ["1939","1941","1945","1950"],       "ans": "1945"},
                {"q": "India gained independence in?",          "opts": ["1945","1946","1947","1948"],       "ans": "1947"},
                {"q": "Magna Carta was signed in?",             "opts": ["1066","1215","1350","1415"],       "ans": "1215"},
                {"q": "Napoleon Bonaparte was from?",           "opts": ["Italy","France","Spain","England"], "ans": "France"},
                {"q": "The printing press was invented by?",    "opts": ["Newton","Gutenberg","Edison","Tesla"], "ans": "Gutenberg"},
                {"q": "American Declaration of Independence: year?", "opts": ["1766","1772","1776","1783"], "ans": "1776"},
            ],
            "World Wars": [
                {"q": "WWI was triggered by assassination of?", "opts": ["Winston Churchill","Adolf Hitler","Archduke Franz Ferdinand","Kaiser Wilhelm"], "ans": "Archduke Franz Ferdinand"},
                {"q": "WWI years?",                             "opts": ["1910-1914","1914-1918","1918-1922","1915-1920"], "ans": "1914-1918"},
                {"q": "Treaty ending WWI?",                     "opts": ["Treaty of Paris","Treaty of Versailles","Treaty of Westphalia","Geneva Convention"], "ans": "Treaty of Versailles"},
                {"q": "US entered WWII after?",                 "opts": ["D-Day","Pearl Harbor attack","Berlin blockade","Battle of Britain"], "ans": "Pearl Harbor attack"},
                {"q": "D-Day landing was in?",                  "opts": ["1942","1943","1944","1945"],       "ans": "1944"},
                {"q": "WWII Axis powers included?",             "opts": ["UK,US,France","Germany,Italy,Japan","USSR,China,UK","France,Germany,Italy"], "ans": "Germany,Italy,Japan"},
                {"q": "WWII ended in?",                         "opts": ["1943","1944","1945","1946"],       "ans": "1945"},
                {"q": "The Holocaust was carried out by?",      "opts": ["Italy","Japan","Germany","USSR"],  "ans": "Germany"},
            ],
        },

        "Geography": {
            "Maps & Coordinates": [
                {"q": "Latitude lines run?",                    "opts": ["north-south","east-west","diagonally","vertically"], "ans": "east-west"},
                {"q": "Longitude lines run?",                   "opts": ["east-west","north-south","diagonally","horizontally"], "ans": "north-south"},
                {"q": "Tropic of Cancer is at?",                "opts": ["0°","23.5° N","23.5° S","66.5° N"], "ans": "23.5° N"},
                {"q": "Prime Meridian passes through?",         "opts": ["Paris","New York","Greenwich","Moscow"], "ans": "Greenwich"},
                {"q": "Equator is at ___ latitude.",            "opts": ["90° N","45° N","0°","23.5° S"],   "ans": "0°"},
                {"q": "Total longitude lines?",                 "opts": ["180","181","360","361"],           "ans": "361"},
                {"q": "International Date Line is at?",         "opts": ["0° longitude","90° E","180° longitude","90° W"], "ans": "180° longitude"},
                {"q": "Smallest continent?",                    "opts": ["Europe","Antarctica","Australia","South America"], "ans": "Australia"},
            ],
            "Climate & Weather": [
                {"q": "The troposphere is the ___ layer of atmosphere.", "opts": ["outermost","middle","innermost/lowest","second"], "ans": "innermost/lowest"},
                {"q": "Monsoon is caused by?",                  "opts": ["rotation of earth","differential heating of land and sea","ocean currents","volcanic eruptions"], "ans": "differential heating of land and sea"},
                {"q": "Climate is measured over ___ years.",    "opts": ["1","5","10","30"],                 "ans": "30"},
                {"q": "Sahara is in which continent?",          "opts": ["Asia","Australia","Africa","South America"], "ans": "Africa"},
                {"q": "Which biome has the most biodiversity?", "opts": ["desert","tundra","tropical rainforest","grassland"], "ans": "tropical rainforest"},
                {"q": "El Niño refers to unusual warming of?",  "opts": ["Indian Ocean","Atlantic Ocean","Pacific Ocean","Arctic Ocean"], "ans": "Pacific Ocean"},
                {"q": "Humidity measures?",                     "opts": ["temperature","wind speed","moisture in air","rainfall"], "ans": "moisture in air"},
                {"q": "Polar regions experience what type of climate?", "opts": ["tropical","temperate","arid","polar/frigid"], "ans": "polar/frigid"},
            ],
        },
    },

    "College": {

        "Programming": {
            "Arrays": [
                {"q": "Array index starts at?",                 "opts": ["0","1","-1","depends on language"], "ans": "0"},
                {"q": "Time complexity of accessing element by index?", "opts": ["O(1)","O(n)","O(log n)","O(n²)"], "ans": "O(1)"},
                {"q": "Searching an unsorted array (worst case)?", "opts": ["O(1)","O(log n)","O(n)","O(n²)"], "ans": "O(n)"},
                {"q": "A 2D array is essentially an?",          "opts": ["array of arrays","linked list","hash table","stack"], "ans": "array of arrays"},
                {"q": "Static array size is determined at?",    "opts": ["runtime","compile time","link time","load time"], "ans": "compile time"},
                {"q": "Python dynamic array equivalent?",       "opts": ["tuple","set","list","dict"],       "ans": "list"},
                {"q": "Inserting at beginning of array: time complexity?", "opts": ["O(1)","O(log n)","O(n)","O(n²)"], "ans": "O(n)"},
                {"q": "Which sorting is best for nearly-sorted array?", "opts": ["Quick sort","Merge sort","Insertion sort","Heap sort"], "ans": "Insertion sort"},
            ],
            "Loops": [
                {"q": "Which loop always executes at least once?", "opts": ["for","while","do-while","foreach"], "ans": "do-while"},
                {"q": "break statement does?",                  "opts": ["restarts loop","exits the loop","skips iteration","none"], "ans": "exits the loop"},
                {"q": "continue statement does?",               "opts": ["exits the loop","skips current iteration","restarts program","none"], "ans": "skips current iteration"},
                {"q": "range(5) in Python produces?",           "opts": ["1 to 5","0 to 4","0 to 5","1 to 4"], "ans": "0 to 4"},
                {"q": "Infinite loop condition is?",            "opts": ["always false","always true","variable","conditional"], "ans": "always true"},
                {"q": "for i in range(2,8,2) gives?",           "opts": ["[2,4,6,8]","[2,4,6]","[0,2,4,6]","[2,3,4,5,6,7]"], "ans": "2,4,6"},
                {"q": "Nested loop: outer runs N, inner M — total iterations?", "opts": ["N+M","N×M","N²","M²"], "ans": "N×M"},
                {"q": "Which loop is best when count is unknown?", "opts": ["for","while","do-while","foreach"], "ans": "while"},
            ],
            "Pointers": [
                {"q": "A pointer stores a?",                    "opts": ["value","memory address","string","function"], "ans": "memory address"},
                {"q": "& operator in C gives?",                 "opts": ["value of variable","address of variable","size of variable","type of variable"], "ans": "address of variable"},
                {"q": "* operator on pointer gives?",           "opts": ["address","value at address","pointer size","null"], "ans": "value at address"},
                {"q": "NULL pointer points to?",                "opts": ["0x000","1x000","garbage","nothing (no valid location)"], "ans": "nothing (no valid location)"},
                {"q": "Pointer arithmetic increments by?",      "opts": ["1 byte always","size of data type","pointer size","2 bytes"], "ans": "size of data type"},
                {"q": "Wild pointer is?",                       "opts": ["null pointer","pointer to freed memory/uninitialized","void pointer","double pointer"], "ans": "pointer to freed memory/uninitialized"},
                {"q": "int *p; p points to type?",              "opts": ["char","float","int","double"],     "ans": "int"},
                {"q": "Dangling pointer arises when?",          "opts": ["pointer not initialized","pointed memory freed","pointer is null","pointer to function"], "ans": "pointed memory freed"},
            ],
            "Functions": [
                {"q": "Return type of void function?",          "opts": ["int","string","nothing/void","bool"], "ans": "nothing/void"},
                {"q": "Function that calls itself is?",         "opts": ["overloaded","recursive","inline","virtual"], "ans": "recursive"},
                {"q": "Pass by value means?",                   "opts": ["original is modified","a copy is passed","pointer is passed","reference is passed"], "ans": "a copy is passed"},
                {"q": "Default parameter must be at?",          "opts": ["beginning","middle","end","anywhere"], "ans": "end"},
                {"q": "Lambda is a(n)?",                        "opts": ["class method","anonymous function","named function","virtual function"], "ans": "anonymous function"},
                {"q": "Variable scope inside function is?",     "opts": ["global","local","static","extern"], "ans": "local"},
                {"q": "Function overloading is resolved at?",   "opts": ["runtime","compile time","link time","load time"], "ans": "compile time"},
                {"q": "Calling convention __cdecl: caller cleans up?", "opts": ["false","true","depends","never"], "ans": "true"},
            ],
            "Recursion": [
                {"q": "Base case stops?",                       "opts": ["the main program","recursion","compilation","memory allocation"], "ans": "recursion"},
                {"q": "Without base case, recursion causes?",   "opts": ["infinite loop","stack overflow","heap overflow","segfault"], "ans": "stack overflow"},
                {"q": "Fibonacci (naive): time complexity?",    "opts": ["O(n)","O(n log n)","O(2^n)","O(n²)"], "ans": "O(2^n)"},
                {"q": "Tower of Hanoi with n disks: moves needed?", "opts": ["n","2n","2^n − 1","n²"],      "ans": "2^n − 1"},
                {"q": "Recursion uses which structure internally?", "opts": ["queue","heap","stack","tree"], "ans": "stack"},
                {"q": "Tail recursion can be optimized to?",    "opts": ["iteration","heap allocation","dynamic programming","memoization"], "ans": "iteration"},
                {"q": "Memoization in recursion helps with?",   "opts": ["base cases","overlapping subproblems","stack depth","pointer issues"], "ans": "overlapping subproblems"},
                {"q": "Mutual recursion: A calls B and B calls?", "opts": ["main","A","C","itself"],         "ans": "A"},
            ],
        },

        "Mathematics": {
            "Calculus": [
                {"q": "Derivative of x² is?",                   "opts": ["x","2","2x","x²"],                "ans": "2x"},
                {"q": "Integral of 2x dx is?",                  "opts": ["x","2x²","x² + C","2 + C"],      "ans": "x² + C"},
                {"q": "d/dx(sin x) = ?",                        "opts": ["−sin x","cos x","−cos x","tan x"], "ans": "cos x"},
                {"q": "Limit of sin(x)/x as x → 0?",           "opts": ["0","∞","−1","1"],                 "ans": "1"},
                {"q": "Product rule: d/dx(uv) = ?",             "opts": ["u'v'","u'+v'","u'v + uv'","u'v − uv'"], "ans": "u'v + uv'"},
                {"q": "d/dx(eˣ) = ?",                           "opts": ["xeˣ","eˣ−1","eˣ","e"],           "ans": "eˣ"},
                {"q": "∫ e^x dx = ?",                           "opts": ["e^x + C","xe^x","e^(x+1)","1/e^x + C"], "ans": "e^x + C"},
                {"q": "A function has a local max where f'(x) = ?", "opts": ["positive","negative","0 and changes from + to −","0 and changes from − to +"], "ans": "0 and changes from + to −"},
            ],
            "Linear Algebra": [
                {"q": "Determinant of identity matrix?",         "opts": ["0","−1","1","∞"],                 "ans": "1"},
                {"q": "Rank of zero matrix?",                   "opts": ["1","-1","0","undefined"],         "ans": "0"},
                {"q": "Transpose of (AB) = ?",                   "opts": ["A^T B^T","B^T A^T","AB^T","A^T B"], "ans": "B^T A^T"},
                {"q": "Eigenvalue satisfies Av = ?",            "opts": ["Av","λv","0","v+λ"],              "ans": "λv"},
                {"q": "A matrix is invertible when det(A) ≠ ?", "opts": ["1","∞","0","−1"],                 "ans": "0"},
                {"q": "Dot product of orthogonal vectors is?",  "opts": ["1","-1","0","∞"],                 "ans": "0"},
                {"q": "A 3×4 matrix has how many elements?",    "opts": ["7","9","12","16"],                "ans": "12"},
                {"q": "Span of a vector set is?",               "opts": ["largest element","all linear combinations","dot product","determinant"], "ans": "all linear combinations"},
            ],
            "Statistics": [
                {"q": "Mean of 2, 4, 6, 8, 10?",               "opts": ["4","5","6","7"],                  "ans": "6"},
                {"q": "Median of 1, 3, 5, 7, 9?",              "opts": ["3","4","5","6"],                  "ans": "5"},
                {"q": "Mode is the most ___ value.",            "opts": ["average","extreme","frequent","recent"], "ans": "frequent"},
                {"q": "Standard deviation measures?",           "opts": ["central tendency","spread","skewness","kurtosis"], "ans": "spread"},
                {"q": "P(A) + P(A') = ?",                      "opts": ["0","0.5","1","2"],                "ans": "1"},
                {"q": "Normal distribution is shaped like?",    "opts": ["J-curve","U-curve","bell curve","S-curve"], "ans": "bell curve"},
                {"q": "Correlation of −1 means?",               "opts": ["no relation","perfect positive","perfect negative","weak positive"], "ans": "perfect negative"},
                {"q": "Variance is the ___ of standard deviation.", "opts": ["square","square root","reciprocal","logarithm"], "ans": "square"},
            ],
            "Discrete Math": [
                {"q": "P(n,r) = n! / ?",                        "opts": ["r!","(n−r)!","(n+r)!","n!⋅r!"],  "ans": "(n−r)!"},
                {"q": "C(5,2) = ?",                             "opts": ["5","8","10","12"],                "ans": "10"},
                {"q": "A∪B means?",                             "opts": ["elements in both A and B","elements in A or B or both","elements only in A","elements only in B"], "ans": "elements in A or B or both"},
                {"q": "¬(A ∧ B) ≡ ? (De Morgan's)",            "opts": ["¬A ∧ ¬B","¬A ∨ ¬B","A ∨ B","¬A ∧ B"], "ans": "¬A ∨ ¬B"},
                {"q": "Number of subsets of a set with n elements?", "opts": ["n","2n","2^n","n!"],         "ans": "2^n"},
                {"q": "A function is bijective if it is?",      "opts": ["surjective only","injective only","injective and surjective","neither"], "ans": "injective and surjective"},
                {"q": "Pigeonhole: n+1 pigeons in n holes means?", "opts": ["some holes empty","some hole has ≥2","all holes full","one hole empty"], "ans": "some hole has ≥2"},
                {"q": "log₂(1024) = ?",                         "opts": ["8","9","10","11"],                "ans": "10"},
            ],
        },

        "CS Core": {
            "Data Structures": [
                {"q": "Stack follows ___ principle.",           "opts": ["FIFO","LIFO","Random","Priority"], "ans": "LIFO"},
                {"q": "Queue follows ___ principle.",           "opts": ["LIFO","FIFO","Random","Priority"], "ans": "FIFO"},
                {"q": "Hash table average search time?",        "opts": ["O(n)","O(log n)","O(1)","O(n²)"], "ans": "O(1)"},
                {"q": "Linked list head points to?",            "opts": ["last node","middle node","first node","null"], "ans": "first node"},
                {"q": "BST in-order traversal gives?",          "opts": ["random order","sorted order","reverse sorted","level order"], "ans": "sorted order"},
                {"q": "Min-heap root is the?",                  "opts": ["largest element","smallest element","median","middle element"], "ans": "smallest element"},
                {"q": "Which DS uses FIFO?",                    "opts": ["stack","priority queue","queue","tree"], "ans": "queue"},
                {"q": "Deque stands for?",                      "opts": ["double ended queue","dual entry queue","dynamic equilateral queue","none"], "ans": "double ended queue"},
            ],
            "Algorithms": [
                {"q": "Merge sort time complexity (all cases)?", "opts": ["O(n)","O(n²)","O(n log n)","O(log n)"], "ans": "O(n log n)"},
                {"q": "Bubble sort worst case?",                "opts": ["O(n)","O(n log n)","O(n²)","O(2^n)"], "ans": "O(n²)"},
                {"q": "Binary search requires ___ array.",      "opts": ["random","reverse sorted","sorted","hashed"], "ans": "sorted"},
                {"q": "DFS uses which structure?",              "opts": ["queue","heap","stack","hash map"],  "ans": "stack"},
                {"q": "BFS uses which structure?",              "opts": ["stack","heap","queue","tree"],      "ans": "queue"},
                {"q": "Greedy algorithm makes choices that are?", "opts": ["globally optimal","locally optimal","random","brute force"], "ans": "locally optimal"},
                {"q": "Dynamic Programming solves by?",         "opts": ["recursion only","dividing into subproblems and storing solutions","greedy choices","backtracking"], "ans": "dividing into subproblems and storing solutions"},
                {"q": "Quick sort worst case (bad pivot)?",     "opts": ["O(n)","O(n log n)","O(n²)","O(n³)"], "ans": "O(n²)"},
            ],
            "Operating Systems": [
                {"q": "Deadlock requires how many conditions?", "opts": ["2","3","4","5"],                  "ans": "4"},
                {"q": "Virtual memory uses ___ as extension.", "opts": ["RAM","ROM","hard disk","cache"],   "ans": "hard disk"},
                {"q": "FCFS stands for?",                       "opts": ["First Come First Served","Fast CPU First Scheduled","First Cache First Served","none"], "ans": "First Come First Served"},
                {"q": "Paging uses fixed-size units called?",   "opts": ["frames","segments","blocks","sectors"], "ans": "frames"},
                {"q": "Semaphore is used for?",                 "opts": ["memory allocation","process synchronization","file management","I/O buffering"], "ans": "process synchronization"},
                {"q": "Context switch saves and restores?",     "opts": ["only registers","only stack","process state (PCB)","file handles"], "ans": "process state (PCB)"},
                {"q": "Thrashing occurs when?",                 "opts": ["CPU is idle","too many page faults","disk is full","cache is Miss"], "ans": "too many page faults"},
                {"q": "Round Robin scheduling is?",             "opts": ["non-preemptive","preemptive","priority-based","random"], "ans": "preemptive"},
            ],
            "DBMS": [
                {"q": "SQL stands for?",                        "opts": ["Structured Query Language","Simple Query Language","Sequential Query Logic","Standard Query Listing"], "ans": "Structured Query Language"},
                {"q": "Primary key is?",                        "opts": ["can be null","unique + not null","can repeat","foreign key"], "ans": "unique + not null"},
                {"q": "JOIN combines rows from?",               "opts": ["one table only","multiple tables","views only","indexes"], "ans": "multiple tables"},
                {"q": "ACID — 'C' stands for?",                 "opts": ["Commit","Concurrency","Consistency","Cascade"], "ans": "Consistency"},
                {"q": "Normalization reduces?",                 "opts": ["queries","data redundancy","joins","indexes"], "ans": "data redundancy"},
                {"q": "Which SQL command retrieves data?",      "opts": ["INSERT","UPDATE","SELECT","DELETE"], "ans": "SELECT"},
                {"q": "Foreign key references ___ of another table.", "opts": ["any column","primary key","foreign key","null values"], "ans": "primary key"},
                {"q": "GROUP BY is used with?",                 "opts": ["WHERE","ORDER BY","aggregate functions","JOIN"], "ans": "aggregate functions"},
            ],
        },

        "Machine Learning": {
            "Supervised Learning": [
                {"q": "Supervised learning requires?",          "opts": ["unlabeled data","labeled data","no data","only test data"], "ans": "labeled data"},
                {"q": "Linear regression predicts ___ output.", "opts": ["discrete","categorical","continuous","binary"], "ans": "continuous"},
                {"q": "Classification output is?",              "opts": ["continuous","categorical","numeric","unbounded"], "ans": "categorical"},
                {"q": "Overfitting means model performs well on?", "opts": ["test data only","training data only","both","neither"], "ans": "training data only"},
                {"q": "Cross-validation helps evaluate?",       "opts": ["training speed","model generalisation","feature importance","data cleaning"], "ans": "model generalisation"},
                {"q": "Decision tree splits by?",               "opts": ["random choice","highest information gain","majority class","nearest neighbor"], "ans": "highest information gain"},
                {"q": "L2 regularization adds ___ penalty.",    "opts": ["absolute value","squared value","log value","exponential value"], "ans": "squared value"},
                {"q": "Bias-variance tradeoff: high bias means?", "opts": ["overfitting","underfitting","perfect fit","high variance"], "ans": "underfitting"},
            ],
            "Unsupervised Learning": [
                {"q": "K-Means clustering requires specifying?", "opts": ["training labels","number of clusters k","distance metric only","max depth"], "ans": "number of clusters k"},
                {"q": "PCA reduces?",                           "opts": ["number of samples","dimensionality","labels","noise only"], "ans": "dimensionality"},
                {"q": "Unsupervised learning uses ___ data.",   "opts": ["labeled","unlabeled","mixed","synthetic"], "ans": "unlabeled"},
                {"q": "DBSCAN finds clusters of ___ shape.",    "opts": ["circles only","arbitrary shape","squares only","grids"], "ans": "arbitrary shape"},
                {"q": "Hierarchical clustering output is a?",   "opts": ["flat cluster","dendrogram","confusion matrix","scatter plot"], "ans": "dendrogram"},
                {"q": "Elbow method is used to choose?",        "opts": ["learning rate","k in k-means","tree depth","epochs"], "ans": "k in k-means"},
                {"q": "Autoencoders learn to?",                 "opts": ["classify data","generate labels","compress and reconstruct data","predict sequences"], "ans": "compress and reconstruct data"},
                {"q": "Silhouette score measures?",             "opts": ["accuracy","cluster quality","error rate","loss"], "ans": "cluster quality"},
            ],
            "Neural Networks": [
                {"q": "Activation function introduces?",        "opts": ["linearity","non-linearity","randomness","sparsity"], "ans": "non-linearity"},
                {"q": "Backpropagation computes?",              "opts": ["forward pass","loss gradient w.r.t weights","predictions","data splits"], "ans": "loss gradient w.r.t weights"},
                {"q": "Dropout prevents?",                      "opts": ["underfitting","overfitting","vanishing gradients","data leakage"], "ans": "overfitting"},
                {"q": "ReLU(x) for x < 0 returns?",            "opts": ["x","−x","1","0"],                 "ans": "0"},
                {"q": "CNN is best for?",                       "opts": ["text","time series","image data","tabular data"], "ans": "image data"},
                {"q": "LSTM solves the ___ problem.",           "opts": ["vanishing gradient","overfitting","underfitting","dimensionality"], "ans": "vanishing gradient"},
                {"q": "Softmax output values sum to?",          "opts": ["0","−1","1","100"],               "ans": "1"},
                {"q": "Number of parameters in dense layer (n inputs, m outputs)?", "opts": ["n+m","n×m","n×m + m","n²"], "ans": "n×m + m"},
            ],
        },
    },
}

# ── Keyword map for PDF analysis ─────────────────────────────────────────────
_PDF_KEYWORDS: Dict[str, List[str]] = {
    "Arrays"              : ["array","index","element","list","subscript","vector"],
    "Loops"               : ["loop","for","while","iteration","iterate","repeat"],
    "Pointers"            : ["pointer","address","memory","dereference","null","reference"],
    "Functions"           : ["function","method","return","parameter","argument","call"],
    "Recursion"           : ["recursion","recursive","base case","stack overflow","factorial"],
    "Calculus"            : ["derivative","integral","limit","differentiation","integration","function"],
    "Linear Algebra"      : ["matrix","vector","eigenvalue","determinant","transpose","rank"],
    "Statistics"          : ["mean","median","mode","variance","standard deviation","probability"],
    "Data Structures"     : ["stack","queue","tree","graph","hash","linked list"],
    "Algorithms"          : ["algorithm","sort","search","complexity","big o","greedy","dynamic programming"],
    "Operating Systems"   : ["process","thread","deadlock","scheduling","memory","paging","semaphore"],
    "DBMS"                : ["database","sql","query","table","primary key","normalization","join"],
    "Machine Learning"    : ["model","training","classification","regression","neural","feature","accuracy"],
    "Supervised Learning" : ["labeled","train","test","overfitting","bias","variance","cross-validation"],
    "Neural Networks"     : ["neuron","activation","backpropagation","cnn","lstm","dropout","gradient"],
}


# ── Public API ────────────────────────────────────────────────────────────────

def get_question_set(
    role: str,
    subject: str,
    topic: str,
    n: int = 5,
) -> List[Dict]:
    """
    Return n randomly sampled questions for the given role/subject/topic.

    Args:
        role    : 'School' or 'College'.
        subject : One of the subjects in SUBJECTS[role].
        topic   : One of the topics in SUBJECTS[role][subject].
        n       : Number of questions to return (capped at available).

    Returns:
        List of question dicts: [{q, opts, ans}, ...].

    Raises:
        ValueError if role/subject/topic not found.
    """
    try:
        pool = QUESTION_BANK[role][subject][topic]
    except KeyError:
        raise ValueError(
            f"No questions found for role='{role}', subject='{subject}', topic='{topic}'.\n"
            f"Available: {json.dumps(SUBJECTS.get(role, {}), indent=2)}"
        )

    n = min(n, len(pool))
    return random.sample(pool, n)


def _compute_score(answers: Dict[str, List[bool]]) -> float:
    total = sum(len(v) for v in answers.values())
    correct = sum(sum(bool(a) for a in v) for v in answers.values())
    return round((correct / total) * 100, 2) if total else 0.0


def _classify_level(score: float) -> str:
    if score >= 75: return "Advanced"
    if score >= 45: return "Intermediate"
    return "Beginner"


def _find_weak(answers: Dict[str, List[bool]], threshold: float = 0.5) -> List[str]:
    return [
        concept for concept, ans in answers.items()
        if ans and (sum(bool(a) for a in ans) / len(ans)) < threshold
    ]


def _compute_retention(flat: List[bool]) -> str:
    recent = [bool(a) for a in flat[-3:]] if len(flat) >= 3 else [bool(a) for a in flat]
    ratio = sum(recent) / len(recent) if recent else 0
    if ratio >= 0.67: return "High"
    if ratio >= 0.34: return "Medium"
    return "Low"


def _get_resources(concepts: List[str], role: str) -> Dict[str, str]:
    level_map = _RESOURCES.get(role, {})
    flat: Dict[str, str] = {}
    for subj in level_map.values():
        if isinstance(subj, dict):
            flat.update(subj)

    result = {}
    for c in concepts:
        if c in flat:
            result[c] = flat[c]
        else:
            # Search across all roles
            for bucket in _RESOURCES.values():
                if isinstance(bucket, dict):
                    for subj_resources in bucket.values():
                        if isinstance(subj_resources, dict) and c in subj_resources:
                            result[c] = subj_resources[c]
                            break
            if c not in result:
                result[c] = f"Search '{c}' on GeeksforGeeks, Khan Academy, or YouTube."
    return result


def _build_plan(weak: List[str], level: str, score: float) -> List[str]:
    plan = []
    if score < 45:
        plan += [
            "Day 1-2: Revisit core lecture notes for all weak topics.",
            "Day 3-4: Attempt beginner-level problems (Khan Academy / LeetCode Easy).",
            "Day 5  : Mini self-quiz on revised topics.",
            "Day 6-7: Spaced repetition — one weak concept per day using flashcards.",
        ]
    elif score < 75:
        plan += [
            "Day 1  : Review notes, highlight gaps per weak concept.",
            "Day 2-3: Solve medium-difficulty problems for each weak topic.",
            "Day 4  : Full timed mock quiz across all concepts.",
            "Day 5-7: Spaced repetition — one weak concept per day.",
        ]
    else:
        plan += [
            "Day 1-2: Tackle advanced / hard-level problems.",
            "Day 3  : Mixed-topic problems for cross-concept fluency.",
            "Day 4  : Full timed assessment under exam conditions.",
            "Day 5-7: Explore real-world projects (Kaggle / HackerRank / GitHub).",
        ]
    if weak:
        plan.append(f"Priority focus: {', '.join(weak)} — 20+ min/day.")
    plan.append(f"Current level: {level} — aim for next level in 2 weeks.")
    return plan


def evaluate_performance(
    data: Dict[str, List[bool]],
    student_name: str = "Unknown",
    student_level: str = "School",
) -> Dict[str, Any]:
    """
    Full adaptive evaluation pipeline.

    Args:
        data          : {concept_name: [bool, bool, ...]} — answers per concept.
        student_name  : Student's display name.
        student_level : 'School' or 'College'.

    Returns:
        Comprehensive result dict.
    """
    if not isinstance(data, dict) or not data:
        raise ValueError("data must be a non-empty dict of {concept: [bool, ...]}.")

    score       = _compute_score(data)
    level       = _classify_level(score)
    weak        = _find_weak(data)
    flat        = [bool(a) for v in data.values() for a in v]
    retention   = _compute_retention(flat)
    resources   = _get_resources(list(data.keys()), student_level)
    plan        = _build_plan(weak, level, score)
    diff_flow   = get_difficulty(flat)
    diff_summary= get_difficulty_summary(flat)
    next_level  = get_next_difficulty(flat, level)

    ai = generate_feedback(
        student_name=student_name,
        concept_score=score,
        speed="Average",
        retention=retention,
        weak_concepts=weak,
        role=student_level,
    )

    result = {
        "student_name"      : student_name,
        "student_level"     : student_level,
        "concept_score"     : score,
        "level"             : level,
        "next_level"        : next_level,
        "weak_concepts"     : weak,
        "resources"         : resources,
        "study_plan"        : plan,
        "speed"             : "Average",
        "retention"         : retention,
        "feedback"          : ai["feedback"],
        "feedback_parts"    : ai["feedback_parts"],
        "difficulty_flow"   : diff_flow,
        "difficulty_summary": diff_summary,
    }

    save_result({
        "student_name" : student_name,
        "concept_score": score,
        "feedback"     : ai["feedback"],
        "level"        : level,
        "weak_concepts": weak,
        "student_level": student_level,
    })

    return result


def extract_pdf_text(pdf_file) -> str:
    """
    Extract text from an uploaded PDF file object using PyPDF2.

    Args:
        pdf_file: File-like object (e.g. from st.file_uploader).

    Returns:
        Extracted text string, or error message starting with 'ERROR:'.
    """
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(pdf_file)
        text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        ).strip()
        return text if text else "ERROR: No readable text found in PDF."
    except Exception as e:
        return f"ERROR: {e}"


def analyze_pdf_content(text: str, student_name: str = "Student") -> Dict[str, Any]:
    """
    Analyse extracted PDF text and generate adaptive feedback.

    Identifies topics using keyword matching, then evaluates conceptual
    depth (keyword density) as a proxy for coverage/understanding.

    Args:
        text         : Raw text extracted from a PDF.
        student_name : Student's name for personalised feedback.

    Returns:
        Dict with identified_topics, topic_scores, concept_score,
        level, weak_topics, resources, study_plan, feedback.
    """
    if not text or text.startswith("ERROR"):
        return {"error": text or "Empty text provided."}

    text_lower = text.lower()
    word_count = max(len(text_lower.split()), 1)

    topic_scores: Dict[str, float] = {}
    for topic, keywords in _PDF_KEYWORDS.items():
        hits = sum(text_lower.count(kw) for kw in keywords)
        density = (hits / word_count) * 1000  # hits per 1000 words
        if hits > 0:
            # Normalise density to 0-100 range (cap at 20 hits/1000 words = 100%)
            topic_scores[topic] = min(round((density / 20) * 100, 1), 100.0)

    if not topic_scores:
        return {
            "error": "No recognisable topics found. "
                     "Try uploading a more technical document."
        }

    identified_topics = sorted(topic_scores, key=topic_scores.get, reverse=True)
    concept_score = round(sum(topic_scores.values()) / len(topic_scores), 2)
    level = _classify_level(concept_score)
    weak_topics = [t for t, s in topic_scores.items() if s < 50]

    # Build answer dict for pipeline compatibility (proxy: high score = all correct)
    proxy_answers: Dict[str, List[bool]] = {}
    for topic, score in topic_scores.items():
        n_proxy = 4
        n_correct = round((score / 100) * n_proxy)
        proxy_answers[topic] = [True] * n_correct + [False] * (n_proxy - n_correct)

    resources = _get_resources(identified_topics[:6], "College")
    plan      = _build_plan(weak_topics[:4], level, concept_score)
    flat_proxy= [a for v in proxy_answers.values() for a in v]
    retention = _compute_retention(flat_proxy)
    ai = generate_feedback(
        student_name=student_name,
        concept_score=concept_score,
        speed="Average",
        retention=retention,
        weak_concepts=weak_topics[:4],
        role="College",
    )

    return {
        "student_name"     : student_name,
        "identified_topics": identified_topics,
        "topic_scores"     : topic_scores,
        "concept_score"    : concept_score,
        "level"            : level,
        "weak_topics"      : weak_topics,
        "resources"        : resources,
        "study_plan"       : plan,
        "retention"        : retention,
        "feedback"         : ai["feedback"],
        "feedback_parts"   : ai["feedback_parts"],
    }


# ── Standalone smoke test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Backend Smoke Test ===\n")

    qs = get_question_set("School", "Math", "Algebra", n=3)
    print(f"Sample questions (School/Math/Algebra): {len(qs)} loaded")
    for q in qs:
        print(f"  Q: {q['q']}  → Ans: {q['ans']}")

    result = evaluate_performance(
        data={"Arrays": [True, False, True, True], "Loops": [False, False, True, False]},
        student_name="Test Student",
        student_level="College",
    )
    print(f"\nScore  : {result['concept_score']}%")
    print(f"Level  : {result['level']}  →  Next: {result['next_level']}")
    print(f"Weak   : {result['weak_concepts']}")
    print(f"Trend  : {result['difficulty_summary']['trend']}")