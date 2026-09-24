## The phenomenon

<!-- What goes up and down, and why you looked at it. -->

Even having moved half-way across the United States when I was younger, I've always lived in what many call: "Tornado Valley". This natural phenomenon was a part of everyday life, with most ignoring tornado warning on their phones having lived through several natural disasters without worry. This has created a fascination within me since a young age and is why I choose tornados for this assignment. Tornados functionally are formed when there is a rush of warm moist air collides with colder dry air. 2 different types of winds rotating against each other as they form the pillar of air labeled as a tornado. 

## The source

<!-- A link to the page or endpoint the file came from, and one line on what is in
the file: how many rows, what a row means, what the units are. -->
https://www.kaggle.com/datasets/danbraswell/us-tornado-dataset-1950-2021

Each 67,558 row includes when and where tornado happened, how powerful it was on F/EF Scale, the number of fatalities and injuries, and wear the tornado originated exactly in USA. This includes only the year of 2021. 

## What the picture shows

<!-- Two or three sentences. Including what it hides: every transformation throws
something away, and naming what yours threw away is the easiest way to sound like
you know what you did. -->

The pictures shows everything except the path the tornados took and the time they formed. I wanted to show the history of tornados in the United States, and including the path width and path length would create visual clutter that wouldn't add anything the visual representation of data. The exact time the tornados formed was also irrelevant for this visualization as it does not change the impact the tornado on the surrounding areas. 

<img width="1073" height="701" alt="Screenshot 2026-09-24 at 4 56 50 PM" src="https://github.com/user-attachments/assets/150a6c41-c385-4804-b02e-8c42cc0306b9" />


## Run it

```
uv run fetch.py
uv run plot.py
```
