# Telegram Bot for Dungeons and Dragons (5e)

This Telegram bot was developed with the aim of providing comprehensive support during a game of Dungeons and Dragons, using the rules of the fifth edition (5e). It offers various features that assist players throughout the game.

## Features

The bot offers the following features:

### 1. Character Creation

Users can interactively create a new character, following the rules of the fifth edition of Dungeons and Dragons. The bot guides the user through the process of choosing each aspect of the character, ensuring a simplified and intuitive character creation experience. Additionally, users have the option to generate some features in a Custom or Automated way to save time.

### 2. Character Viewing

Users can view all characters created previously. This feature allows players to keep track of all their played characters, simplifying the transition between different campaigns and enabling them to play various campaigns with the same character.

### 3. New Campaign Creation

The bot allows users to create new game campaigns. Users can define the name of the campaign and its attribute (Public or Private). A Public campaign will be visible to all players in a common list, while access to a Private campaign requires knowledge of the exact name and password.

### 4. Join a Campaign

Users can join an existing campaign, whether it's a newly created campaign or one they are currently playing. This feature facilitates the management of ongoing campaigns and allows users to participate in different gaming sessions seamlessly. Although users can join multiple campaigns simultaneously, they can actively play only one at a time.

## Bot Usage

1. **Registration**: To access the bot's functionalities, users must register. Registration is automatic and occurs through each user's unique telegramID.

2. **Commands**: The bot does not rely on commands but on guided conversations with the user. Different conversation trees develop around a main menu, to which users are returned after each interaction cycle with the bot, depending on the functionality they want to use.

3. **Interaction**: The bot guides users through all phases of the game and provides intuitive options for other features. Simply follow the bot's instructions to interact with it.

## Requirements

The bot has been developed in Python using the `python-telegram-bot` library. Please make sure you have Python installed on your system before running the bot. In addition to this library, the libraries listed in the "requirements.txt" file have also been used. To install the necessary libraries, execute the following command from a terminal:

```
pip install -r requirements.txt
```

## Starting the Bot

To start the bot, execute the following command:

```
python DnD_bot.py
```

**DISCLAIMER**: In order to get the bot to work, input your telegram token in the terminal during the startup process (after running the python file)