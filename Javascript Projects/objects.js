var movies = [
                {name: "Bugs life", rating: "4 stars", hasWatched : 10},
                {name: "Lion King", rating: "5 stars", hasWatched : 20},
                {name: "Batman", rating: "4.5 stars", hasWatched : 8},
                {name: "The Great Boy", rating: "7 stars", hasWatched : 1}
            ];

movies.forEach(function(movie) {
    console.log("You have watched " + movie.name + " that's rated - " + movie.rating);
});
