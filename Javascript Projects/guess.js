//Create Secret Number
var secretNum = 4;
var guess = Number(prompt("Guess a number:"));

if ((guess === secretNum) == true){
    alert("You guessed it!!");

} else if (guess > secretNum) {
    alert("Too High !!!");

} else {
    alert("Too Low !!!");

}

