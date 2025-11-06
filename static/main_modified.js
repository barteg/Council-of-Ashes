const socket = io({
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000
});

// UI Elements
const storySelectionUI = document.getElementById("story-selection");
const waitingScreenUI = document.getElementById('waiting-screen');
const gameUI = document.getElementById("game-ui");

// Waiting Screen Elements
const playersWaitingContainer = document.getElementById('players-waiting');

// Game UI Elements
const playersDisplayContainer = document.getElementById("players-display");
const storyText = document.getElementById("story-text");
const dilemmaImage = document.getElementById("dilemma-image");
const continueBtn = document.getElementById("continue-btn");

// Audio Elements
const backgroundMusic = new Audio('/static/sounds/background1.mp3');
const swooshSound = new Audio('/static/sounds/swoosh.mp3');

// Game State
let gameId = null;
let storyData;
let currentDilemmaId;
let players = {};
let groups = {};

// ================= SOCKET.IO EVENTS =================

socket.on('game_created', (data) => {
    gameId = data.game_id;
    playersWaitingContainer.innerHTML = ''; // Clear previous players

    for (const [playerId, playerUrl] of Object.entries(data.player_urls)) {
        const playerEl = document.createElement('div');
        playerEl.id = `player-waiting-${playerId}`;
        playerEl.className = 'p-4 bg-gray-800 rounded-lg shadow-lg text-center';
        playerEl.innerHTML = `
            <h3 id="player-name-waiting-${playerId}" class="text-xl font-bold text-white mb-2">Player ID: ${playerId}</h3>
            <div id="qr-code-${playerId}" class="flex justify-center items-center h-48"></div>
            <p id="status-${playerId}" class="text-red-500 font-semibold mt-2">Oczekuje...</p>
        `;
        playersWaitingContainer.appendChild(playerEl);
        generateQRCode(document.getElementById(`qr-code-${playerId}`), playerUrl);
    }

    storySelectionUI.classList.add('hidden');
    waitingScreenUI.classList.remove('hidden');
});

socket.on('player_joined', (data) => {
    for (const [playerId, isJoined] of Object.entries(data)) {
        const statusEl = document.getElementById(`status-${playerId}`);
        if (statusEl) {
            if (isJoined) {
                statusEl.textContent = 'Połączono!';
                statusEl.classList.replace('text-red-500', 'text-green-500');
            } else {
                statusEl.textContent = 'Oczekuje...';
                statusEl.classList.replace('text-green-500', 'text-red-500');
            }
        }
    }
});

socket.on('player_disconnected', (data) => {
    const statusEl = document.getElementById(`status-${data.player_id}`);
    if (statusEl) {
        statusEl.textContent = 'Rozłączono';
        statusEl.classList.replace('text-green-500', 'text-red-500');
    }
});

socket.on('game_update', (data) => {
    const playerNameEl = document.getElementById(`player-name-waiting-${data.player_id}`);
    if (playerNameEl) {
        playerNameEl.textContent = data.data.name;
    }
});

socket.on('start_game', (data) => {
    console.log('Host: Received start_game event.', data);
    players = data.players;
    groups = data.groups;
    
    const storyFile = 'temple_story_data'; // This will be replaced later
    console.log('Host: Attempting to import story module...');

    import(`./${storyFile}.js`).then(module => {
        console.log('Host: Story module imported successfully.', module);
        storyData = module.labyrinthStoryData;
        currentDilemmaId = module.startingDilemmaId;
        console.log('Host: storyData populated:', storyData);
        console.log('Host: startingDilemmaId:', currentDilemmaId);

        waitingScreenUI.classList.add('hidden');
        gameUI.classList.remove('hidden');
        
        updatePlayersDisplay();

        // Start background music
        backgroundMusic.loop = true;
        backgroundMusic.volume = 0.3; // Adjust volume as needed
        backgroundMusic.play().catch(e => console.error("Error playing background music:", e));

        console.log('Host: Calling loadStory().');
        loadStory();
    }).catch(error => {
        console.error('Host: Error importing story module:', error);
    });
});

socket.on('dilemma_resolved', (data) => {
    storyText.innerHTML = `<p class="text-lg leading-relaxed text-gray-200">${data.outcome}</p>`;
    
    currentDilemmaId = data.next_dilemma_id;

    // Make the continue button visible
    continueBtn.classList.remove('hidden');
});

// ================= UI FLOW =================

socket.emit('create_game', { story: 'temple_story_data' });

continueBtn.addEventListener('click', () => {
    swooshSound.volume = 0.7; // Adjust volume as needed
    swooshSound.play().catch(e => console.error("Error playing swoosh sound:", e));
    loadStory();
    continueBtn.classList.add('hidden'); // Hide the button again
});

// ================= GAME LOGIC =================

function loadStory() {
    console.log('Host: Inside loadStory().');
    console.log('Host: currentDilemmaId:', currentDilemmaId);
    console.log('Host: storyData:', storyData);

    if (!currentDilemmaId || !storyData[currentDilemmaId]) {
        storyText.innerHTML = `<h2 class="text-3xl font-bold text-yellow-400">Błąd: Nie znaleziono kolejnego kroku historii!</h2><p>Sprawdź ID dylematu.</p>`;
        return; // Stop execution if there's an error
    }

    const currentStoryCard = storyData[currentDilemmaId];
    console.log('Host: currentStoryCard:', currentStoryCard);

    storyText.innerHTML = `<p class="text-lg leading-relaxed text-gray-200">${currentStoryCard.prompt}</p>`;

    if (currentStoryCard.image) {
        dilemmaImage.src = currentStoryCard.image;
        dilemmaImage.classList.remove('hidden');
    } else {
        dilemmaImage.classList.add('hidden');
    }

    if (currentStoryCard.type === 'dilemma') {
        console.log('Host: Emitting game_event with new_turn (dilemma).');
        socket.emit('game_event', { 
            game_id: gameId, 
            event: 'new_turn', 
            dilemma: currentStoryCard 
        });
    } else if (currentStoryCard.type === 'ending' || currentStoryCard.type === 'final_ending') {
        storyText.innerHTML += `<p class="text-lg leading-relaxed text-gray-200">${currentStoryCard.outcome}</p>`;
        if (currentStoryCard.next) { 
            continueBtn.classList.remove('hidden');
        } else { 
            storyText.innerHTML += `<h2 class="text-3xl font-bold text-yellow-400">Koniec gry!</h2><p>Dziękujemy za grę!</p>`;
        }
        console.log('Host: Emitting game_event with story_end.');
        socket.emit('game_event', { 
            game_id: gameId, 
            event: 'story_end', 
            dilemma: currentStoryCard 
        });
    } else if (currentStoryCard.type === 'transition') {
        storyText.innerHTML += `<p class="text-lg leading-relaxed text-gray-200">${currentStoryCard.outcome}</p>`;
        currentDilemmaId = currentStoryCard.next;
        console.log('Host: Automatically transitioning to:', currentDilemmaId);
        setTimeout(loadStory, 3000);
    } else {
        console.error('Host: Unknown story card type:', currentStoryCard.type);
        storyText.innerHTML = `<h2 class="text-3xl font-bold text-red-500">Błąd: Nieznany typ kroku historii!</h2><p>Typ: ${currentStoryCard.type}</p>`;
    }
}

function updatePlayersDisplay() {
    playersDisplayContainer.innerHTML = '';
    for (const [playerId, player] of Object.entries(players)) {
        const playerEl = document.createElement('div');
        playerEl.id = `player-display-${playerId}`;
        playerEl.className = 'p-4 bg-gray-800 rounded-lg shadow-lg';
        playerEl.innerHTML = `
            <div class="flex items-center">
                <img src="${player.avatar}" class="w-16 h-16 rounded-full mr-4">
                <div>
                    <h3 class="text-xl font-bold text-white">${player.name}</h3>
                    <p class="text-gray-400">Group: ${player.group}</p>
                    <div id="player-params-${playerId}"></div>
                </div>
            </div>
        `;
        playersDisplayContainer.appendChild(playerEl);

        const paramsEl = document.getElementById(`player-params-${playerId}`);
        for (const [paramName, paramValue] of Object.entries(player.parameters)) {
            const paramDiv = document.createElement('div');
            paramDiv.innerHTML = `<span class="font-semibold">${paramName}:</span> ${paramValue}`;
            paramsEl.appendChild(paramDiv);
        }
    }
}

// ================= HELPER FUNCTIONS =================

function generateQRCode(element, url) {
    const qr = qrcode(4, 'L');
    qr.addData(window.location.origin + url);
    qr.make();
    element.innerHTML = qr.createImgTag(6, 4);
}
