var todos = [];

window.setTimeout(function() {
  // put all of your JS code from the lecture here
  var userInput = prompt("What would you like to do?");

  // Stop prompting once user enters quit
    while (userInput !== "quit") {
        if (userInput === "list"){
            todos.forEach(function(userInput)) {
                console.log("*******************");
                console.log(i + ": " + userInput);
                console.log("*******************");
            }
        } else if (userInput === "new") {
            var newTask = prompt("Enter new toDo");
            todos.push(newTask); // add new task to array

        } else if (userInput == "delete") {
            var task = prompt("Enter index of task to delete");
            todos.splice(index, 1)l
            console.log("Deleted task");
        }
        userInput = prompt("What next?");
    }
    console.log(" Goodbye!!");

}, 3000);
