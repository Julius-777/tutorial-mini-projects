/*jslint browser: true*/
/*global $, jQuery, alert*/
// Enable strict mode globally
//"use strict";

/*
    toggle strike through upon clicking on task (li)
 */
$("ul").on("click", "li", function () {
    $(this).toggleClass("completed");

});

/*
    Click on x to delete Todo
 */
$("ul").on("click", "span", function (event) {
    /*remove div by clicking span -> todo task*/
    $(this).parent().fadeOut(500, function () {
        $("this").remove();
    });
    event.stopPropagation();
});

/*
    Pass input through by pressing enter
 */
$("input[type='text']").keypress(function (ev) {
    //check character code is 13 = enter

    if (ev.which === 13) {
        // get input text & clear
        var newinput = $(this).val();
        $(this).val("");
        // Add new li -> todo to the ul on page
        $("ul").append("<li><span class='delete'><i class='fas fa-trash'></i></span>" + newinput + "</li>");
    }

});

/*
    Toggle "Add New Task" placeholder
*/

$("#add").click(function () {
    /* Toggle... */
    $("input[type='text']").fadeToggle();
    $("input[type='text']").transition = "0.1s linear";
});
