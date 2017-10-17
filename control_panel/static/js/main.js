/** Dismiss notification and mark it as read **/
function dismissMessage(messageID) {
    $.ajax({
        type: 'POST',
        url: "/dismiss_message/",
        data: {
            id: messageID,
            "csrfmiddlewaretoken": document.getElementById("token").value,
        },
        success: function(response){
        }
        }).done(function(data){

        });
}

/** Function is called when a message is **/
/** accepted/rejected to mark it as read in the backend **/
function readMessage(messageID, choice, recipient, meeting) {
    updateMessagesBadge(true);
    $("div[id^=" + messageID + "]").remove();
    var messagesLeft = $('.thumbnail').length
    if (messagesLeft == 0) {
        document.getElementById("badgeLabel").innerHTML = 0;
        document.getElementById("alert-messages").innerHTML = "You have no available invitations";
    }
    document.getElementById("badgeLabel").innerHTML = messagesLeft;
    $.ajax({
            type: 'POST',
            url: "/read_message/",
            data: {
                id: messageID,
                action: choice,
                recipient: recipient,
                meeting: meeting,
                "csrfmiddlewaretoken": document.getElementById("token").value,
            },
            success: function(response){
            }
        }).done(function(data){
        });
}

