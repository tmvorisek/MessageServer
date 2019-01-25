ws = {};
id_number = Math.floor((Math.random() * 100000000) + 1)
name = ""



function sendObject(obj) {
    json = JSON.stringify(obj);
    ws.send(json);
}

function addChat(name, message)
{
    var chat = document.getElementById("chat");
    chat.innerHTML += "<b>" + name + "</b> " + message + "<br>";
}

function webSocketConnect() {
    ws = new WebSocket("ws://localhost:8888/ws?Id="+id_number);
    var name_entry = document.getElementById("nameEntry");
    var pass_entry = document.getElementById("passEntry");
    ws.onopen = function() {
        name = name_entry.value;
        sendObject({type:"connect", name:name_entry.value, pass:pass_entry.value});
    };
    ws.onmessage = function (evt) { 
        var msg = JSON.parse(evt.data);
        if (msg["type"] == "connect"){
            addChat("Commons", "User " + msg["name"] + " Connected");
            if (msg["name"] == name){
                var name_entry = document.getElementById("nameEntry");
                var pass_entry = document.getElementById("passEntry");
                var auth = document.getElementById("authenticate");
                name_entry.parentElement.removeChild(name_entry);
                pass_entry.parentElement.removeChild(pass_entry);
                auth.parentElement.removeChild(auth);
            }

        }
        else if (msg["type"] == "chat"){
            addChat(msg["name"], msg["text"]);
        }
    };
    ws.onclose = function() { 

    };
    document.getElementById("chatEntry")
        .addEventListener("keyup", function(event) {
        event.preventDefault();
        if (event.keyCode === 13) {
            document.getElementById("submitChat").click();
        }
    });
}

function sendChat() {
    var chatEntry = document.getElementById("chatEntry");
    var chatMessage = {
        text: chatEntry.value,
        type: "chat",
        id: id_number
    };
    sendObject(chatMessage);

    chatEntry.value = "";
};

function deleteAccount() {
    sendObject({type:"delete"});
}

function makeMove(){
    sendObject({type:"move"});
}

