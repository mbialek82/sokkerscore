# SokkerScore privacy policy

SokkerScore is a browser extension (Chrome, Firefox) that adds a tab with player ratings to the match report on app.sokker.org.
It works only on pages of app.sokker.org and does not read or change any other website.

## What it sends, and to whom

1. When you open the SokkerScore tab, the extension asks the SokkerScore database (a Supabase project hosted in Frankfurt,
   Germany) for the ratings of that match, for a player's history when you open a profile, and for a team's players when you
   use the squad view.
2. If the match is an official match (league, play-offs, cups, national teams) that nobody has rated yet, the extension fetches
   three things from sokker.org using your Sokker session: the data of the match viewer (where the ball and the players were
   during the match), Sokker's match report (line-ups, events, minutes played), and from the line-up only each player's surname,
   age, height and weight and whether he started on the bench. It sends these three files to the SokkerScore database so that
   the match can be rated. This is the match's own data, which every Sokker user can see on sokker.org; browsers' stores call it
   "website content".

## What it does not send

The extension does not send your Sokker login, password or cookies, your team, your name, your browsing or anything else about
you, and it does not know who you are. It stores nothing on your computer beyond what the browser keeps for every extension.
It uses no analytics and no advertising, and no data is sold or given to anyone.

As with any website, the hosting service of the database (Supabase) sees the internet address (IP) that a request comes from,
in its ordinary server logs.

## Shared data

Ratings are shared: a match that any SokkerScore user has opened is visible to all other users, as the match itself is visible
to every Sokker user. The program that works out the ratings and the database layout are public in this repository.

## Contact

Questions: https://github.com/mbialek82/sokkerscore/issues
