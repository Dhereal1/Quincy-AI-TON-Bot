# DAY 3 - If / Else (Decision Making)

# Example 1: Basic age check
age = int(input("How old are you? "))
if age > 18:
    print("adult")
else:
    print("kid")

# Example 2: Food preference with decision
print("\n--- Food Preference ---")
food = input("Amala or Eba? ")
if food == "Amala":
    print("Great choice! Amala is delicious")
else:
    print("I also love " + food)

# Example 3: Multiple conditions (if-elif-else)
print("\n--- Snack Rating ---")
rating = int(input("Rate this snack (1-5): "))
if rating >= 4:
    print("You love it!")
elif rating >= 3:
    print("It's okay")
else:
    print("Not your favorite")
