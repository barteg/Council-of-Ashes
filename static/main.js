const socket = io();

let audioQueue = [];
let isPlaying = false;
let currentAudio = null;
let loadingTimeout;

let loadingSafetyTimeout;

function showLoadingScreen(isPlayerView = false) {
    const loadingOverlay = document.getElementById('loadingOverlay');
    const progressBar = document.getElementById('loadingProgressBar');
    const progressText = document.getElementById('loadingProgressText');
    const loadingMessage = document.getElementById('loadingMessage');

    const funnyMessages = [
        "Retikulacja splajnów...",
        "Generowanie dowcipnych dialogów...",
        "Ostrzenie wideł...",
        "Konsultowanie się ze starszymi bogami...",
        "Polerowanie monokli...",
        "Zaganianie kotów...",
        "Liczenie do nieskończoności (dwa razy)...",
        "Parzenie kawy...",
        "Zdecydowanie nie kradniemy twoich danych...",
        "Przekonywanie chomików do szybszego biegu..."
    ];

    if (loadingMessage) {
        const randomIndex = Math.floor(Math.random() * funnyMessages.length);
        loadingMessage.textContent = funnyMessages[randomIndex];
    }

    if (isPlayerView) {
        const mainContentArea = document.getElementById('mainContentArea');
        if (mainContentArea) mainContentArea.style.display = 'none';
    }

    let progress = 0;
    if (progressBar) progressBar.style.width = '0%';
    if (progressText) progressText.textContent = '0%';
    if (loadingOverlay) loadingOverlay.style.display = 'flex';

    clearTimeout(loadingTimeout);
    clearTimeout(loadingSafetyTimeout); // Clear any existing safety timeout

    // Safety timeout: 30 seconds max loading time
    loadingSafetyTimeout = setTimeout(() => {
        console.warn("Loading timed out (safety mechanism).");
        completeLoading(isPlayerView);
        alert("Operacja trwa zbyt długo. Sprawdź połączenie lub spróbuj odświeżyć stronę.");
    }, 30000);

    function animateProgress() {
        const increment = Math.random() * 5 + 1; // Random increment between 1 and 6
        progress += increment;

        if (progress >= 99) {
            progress = 99;
            if (progressBar) progressBar.style.width = '99%';
            if (progressText) progressText.textContent = '99%';
            return; // Stop the animation
        }

        if (progressBar) progressBar.style.width = `${progress}%`;
        if (progressText) progressText.textContent = `${Math.floor(progress)}%`;

        const delay = Math.random() * 400 + 100; // Random delay between 100ms and 500ms
        loadingTimeout = setTimeout(animateProgress, delay);
    }

    animateProgress();
}

function completeLoading(isPlayerView = false) {
    clearTimeout(loadingTimeout);
    clearTimeout(loadingSafetyTimeout); // Clear safety timeout
    const progressBar = document.getElementById('loadingProgressBar');
    const progressText = document.getElementById('loadingProgressText');
    const loadingOverlay = document.getElementById('loadingOverlay');

    if (progressBar) progressBar.style.width = '100%';
    if (progressText) progressText.textContent = '100%';

    setTimeout(() => {
        if (loadingOverlay) loadingOverlay.style.display = 'none';
        if (isPlayerView) {
            const mainContentArea = document.getElementById('mainContentArea');
            if (mainContentArea) mainContentArea.style.display = 'block';
        }
    }, 500); // Wait half a second before hiding
}

function playNarration(text) {
    return new Promise((resolve, reject) => {
        if (!text || text.trim() === '') {
            resolve();
            return;
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            controller.abort();
            console.warn('TTS request timed out.');
            resolve(); // Resolve anyway to unblock UI
        }, 10000); // 10 second timeout

        fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text }),
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) throw new Error('Network response was not ok');
            return response.blob();
        })
        .then(blob => {
            const audioUrl = URL.createObjectURL(blob);
            currentAudio = new Audio(audioUrl);
            currentAudio.play();
            currentAudio.onended = () => {
                currentAudio = null;
                // This part is for queuing, not directly related to the loading promise
            };
            resolve(); // Resolve the promise once audio is ready and starts playing
        })
        .catch(error => {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                console.warn('TTS fetch aborted due to timeout.');
            } else {
                console.error('Error fetching TTS audio:', error);
            }
            // Resolve anyway to ensure UI unblocks
            resolve(); 
        });
    });
}

function playNextInQueue() {
    if (audioQueue.length === 0) {
        isPlaying = false;
        return;
    }

    isPlaying = true;
    const text = audioQueue.shift();
    playNarration(text).catch(error => {
        console.error("Error playing narration from queue:", error);
    }).finally(() => {
        playNextInQueue();
    });
}

function updateHostFactionObjectives(factions) {
    const factionObjectivesContainer = document.getElementById('factionObjectivesContainer');
    if (factionObjectivesContainer && factions) {
        factionObjectivesContainer.innerHTML = ''; // Clear previous objectives

        for (const factionId in factions) {
            const factionData = factions[factionId];
            const completedObjectives = factionData.objectives.filter(obj => obj.completed).length;
            const totalObjectives = factionData.objectives.length;

            const factionDiv = document.createElement('div');
            factionDiv.classList.add('floating-element', 'mb-4');
            factionDiv.innerHTML = `
                <h5>${factionId}</h5>
                <p>${completedObjectives} / ${totalObjectives} celów ukończonych</p>
            `;
            factionObjectivesContainer.appendChild(factionDiv);
        }
    }
}


const gameId = document.getElementById('gameId') ? document.getElementById('gameId').textContent.trim() : null;
const playerId = document.getElementById('playerId') ? document.getElementById('playerId').textContent.trim() : null;

const waitingRoom = document.getElementById('waitingRoom');
const gameArea = document.getElementById('gameArea');
const nameSetup = document.getElementById('nameSetup');
const factionSelection = document.getElementById('factionSelection');

const playerNameSpan = document.getElementById('playerName');
const currentRoundSpan = document.getElementById('currentRound');

// Host global stat elements
const hostStatStability = document.getElementById('hostStatStability');
const hostStatEconomy = document.getElementById('hostStatEconomy');
const hostStatFaith = document.getElementById('hostStatFaith');

const dilemmaTitle = document.getElementById('dilemmaTitle');
const dilemmaImage = document.getElementById('dilemmaImage');
const dilemmaDescription = document.getElementById('dilemmaDescription');
const playerStatementInput = document.getElementById('playerStatementInput');
const submitStatementBtn = document.getElementById('submitStatementBtn');

const narrativeOutput = document.getElementById('narrativeOutput');
const narrativeText = document.getElementById('narrativeText');
const nextRoundBtn = document.getElementById('nextRoundBtn');

let playerChoice = null;
let lastSubmittedStatement = ''; // New variable to store the last submitted statement
let clientGlobalStats = { Stability: 50, Economy: 50, Faith: 50 };

if (nextRoundBtn) {
    nextRoundBtn.addEventListener('click', () => {
        showLoadingScreen(true);
        socket.emit('player_action', { game_id: gameId, player_id: playerId, event: 'next_round' });
        nextRoundBtn.disabled = true;
    });
}

// This listener is now global to be heard by the host
socket.on('game_started_for_player', (initial_game_state) => {
    console.log('[DEBUG] game_started_for_player event received');
    const hostControl = document.getElementById('hostControl');
    const lobbyControl = document.getElementById('lobbyControl');

    if (hostControl) { // hostGameArea is removed, so we only check for hostControl
        // Host
        console.log('[DEBUG] Client is host, updating UI');
        document.getElementById('gameSetup').style.display = 'none'; // Explicitly hide gameSetup
        if(lobbyControl) lobbyControl.style.display = 'none'; // Hide lobby controls
        hostControl.style.display = 'block'; // Ensure hostControl is visible

        // Now, make the game-specific elements within hostControl visible
        document.getElementById('hostStatStability').parentElement.parentElement.style.display = 'block'; // Parent of progress bar
        document.getElementById('hostStatEconomy').parentElement.parentElement.style.display = 'block';
        document.getElementById('hostStatFaith').parentElement.parentElement.style.display = 'block';
        document.getElementById('hostNarrative').parentElement.style.display = 'block'; // Parent of narrative
        document.getElementById('hostNarrative').style.display = 'block'; // Make the narrative text itself visible

        updateHostFactionObjectives(initial_game_state.factions);

    } else if (gameArea) {
        // Player
        showLoadingScreen(true);
        waitingRoom.style.display = 'none';
        gameArea.style.display = 'block';
        console.log(`[DEBUG] game_started_for_player: gameArea.style.display after setting: ${gameArea.style.display}`);

        if (initial_game_state.global_stats) {
            updatePlayerStatsBars(initial_game_state.global_stats);
        }

        // Initial update of player-specific stats and faction
        if (initial_game_state && initial_game_state.players && initial_game_state.players[playerId]) {
            const player = initial_game_state.players[playerId];
            playerNameSpan.textContent = player.name;
            currentFactionId = player.faction; // Store faction ID globally

            // Apply Asymmetric UI
            const labelElement = document.querySelector('label[for="playerStatementInput"]');
            if (playerStatementInput) playerStatementInput.placeholder = getFactionPlaceholder(currentFactionId);
            if (labelElement) labelElement.textContent = getFactionLabel(currentFactionId);

            
            // Populate Target Dropdown
            const targetPlayerSelect = document.getElementById('targetPlayerSelect');
            if (targetPlayerSelect) {
                targetPlayerSelect.innerHTML = '';
                for (const pid in initial_game_state.players) {
                    if (pid !== playerId && initial_game_state.players[pid].action_status !== 'empty') {
                        const option = document.createElement('option');
                        option.value = pid;
                        option.textContent = initial_game_state.players[pid].name;
                        targetPlayerSelect.appendChild(option);
                    }
                }
            }
        }
    }
});

socket.on('game_event', async (data) => {
    console.log('Game Event:', data);
    if (data.event === 'dilemma_prompt') {
        const dilemma = JSON.parse(data.dilemma_json);

        // Check if we are on the host page
        if (document.getElementById('hostControl')) {
            showLoadingScreen(false);
            console.log('[DEBUG] Host Dilemma Description:', dilemma.description);
            document.getElementById('hostNarrative').textContent = dilemma.description;
            
            try {
                await playNarration(dilemma.description); // AI NARRATOR
            } catch (error) {
                console.error("Failed to play narration:", error);
            } finally {
                completeLoading(false);
            }

            // Update host global stats progress bars
            const globalStats = data.global_stats;
            if (globalStats) {
                updatePlayerStatsBars(globalStats);
                const hostStatStability = document.getElementById('hostStatStability');
                const hostStatEconomy = document.getElementById('hostStatEconomy');
                const hostStatFaith = document.getElementById('hostStatFaith');

                if (hostStatStability) {
                    hostStatStability.style.width = `${globalStats.Stability}%`;
                    hostStatStability.setAttribute('aria-valuenow', globalStats.Stability);
                    hostStatStability.textContent = `${globalStats.Stability}`;
                }

                if (hostStatEconomy) {
                    hostStatEconomy.style.width = `${globalStats.Economy}%`;
                    hostStatEconomy.setAttribute('aria-valuenow', globalStats.Economy);
                    hostStatEconomy.textContent = `${globalStats.Economy}`;
                }

                if (hostStatFaith) {
                    hostStatFaith.style.width = `${globalStats.Faith}%`;
                    hostStatFaith.setAttribute('aria-valuenow', globalStats.Faith);
                    hostStatFaith.textContent = `${globalStats.Faith}`;;
                }
            }
        } else {
             // If not host (i.e., player), complete the loading screen started by 'game_started_for_player'
            completeLoading(true);
        }

        // Check if we are on the player page
        if (document.getElementById('gameArea')) {
            console.log('[DEBUG] Player Dilemma Object:', dilemma);
            dilemmaTitle.textContent = dilemma.title;
            dilemmaDescription.textContent = dilemma.description;

            const dilemmaSection = document.getElementById('dilemmaSection');
            const playerStatementsSection = document.getElementById('playerStatementsSection');
            const statementVoteSection = document.getElementById('statementVoteSection');


            console.log(`[DEBUG] dilemma_prompt: gameArea.style.display: ${gameArea.style.display}`);
            console.log(`[DEBUG] dilemma_prompt: dilemmaSection.style.display BEFORE: ${dilemmaSection ? dilemmaSection.style.display : 'N/A'}`);
            console.log(`[DEBUG] dilemma_prompt: playerStatementsSection.style.display BEFORE: ${playerStatementsSection ? playerStatementsSection.style.display : 'N/A'}`);
            console.log(`[DEBUG] dilemma_prompt: statementVoteSection.style.display BEFORE: ${statementVoteSection ? statementVoteSection.style.display : 'N/A'}`);


            const currentRoundSpan = document.getElementById('currentRound');
            if (currentRoundSpan) {
                currentRoundSpan.textContent = data.current_round;
            }
            const narrativeOutput = document.getElementById('narrativeOutput');
            if (narrativeOutput) {
                narrativeOutput.style.display = 'none';
            }
            if (nextRoundBtn) {
                nextRoundBtn.style.display = 'none';
            }
            if (dilemmaSection) { // Ensure dilemmaSection is visible for making a choice
                dilemmaSection.style.display = 'block';
                console.log(`[DEBUG] dilemma_prompt: dilemmaSection.style.display after setting: ${dilemmaSection.style.display}`);
            }
            if (playerStatementsSection) { // Ensure playerStatementsSection is initially hidden
                playerStatementsSection.style.display = 'block'; // Show statement input immediately
                
                // CRITICAL FIX: Unhide the internal sections that were hidden after submission
                const playerInputSection = document.getElementById('playerInputSection');
                const statementSubmitted = document.getElementById('statementSubmitted');
                
                if (playerInputSection) playerInputSection.style.display = 'block';
                if (statementSubmitted) statementSubmitted.style.display = 'none';

                console.log(`[DEBUG] dilemma_prompt: playerStatementsSection.style.display after setting: ${playerStatementsSection.style.display}`);

                // Render Suggestions
                const suggestionsContainer = document.getElementById('statementSuggestions');
                if (suggestionsContainer) {
                    suggestionsContainer.innerHTML = ''; // Clear previous
                    if (dilemma.choices && dilemma.choices.length > 0) {
                        dilemma.choices.forEach(choice => {
                            const btn = document.createElement('button');
                            btn.classList.add('btn', 'btn-outline-secondary', 'btn-sm');
                            btn.textContent = choice.text;
                            btn.title = choice.type; // Tooltip
                            btn.style.marginRight = '5px';
                            btn.style.marginBottom = '5px';
                            btn.onclick = (e) => {
                                e.preventDefault(); // Prevent form submission if inside form
                                if (playerStatementInput) {
                                    playerStatementInput.value = choice.text;
                                    // Optional: Flash effect to show it was applied
                                    playerStatementInput.classList.add('bg-light');
                                    setTimeout(() => playerStatementInput.classList.remove('bg-light'), 200);
                                }
                            };
                            suggestionsContainer.appendChild(btn);
                        });
                    }
                }
            }
            if (statementVoteSection) { // Ensure statementVoteSection is initially hidden
                statementVoteSection.style.display = 'none';
                console.log(`[DEBUG] dilemma_prompt: statementVoteSection.style.display after setting: ${statementVoteSection.style.display}`);
            }
            waitingRoom.style.display = 'none';
            if(nextRoundBtn) {
                nextRoundBtn.disabled = false;
            }

            lastSubmittedStatement = ''; // Reset for the new round

            // Reset statement input for new round
            const playerInputSection = document.getElementById('playerInputSection');
            const statementSubmitted = document.getElementById('statementSubmitted');
            if (playerStatementInput) {
                playerStatementInput.value = '';
            }
            if (playerInputSection) {
                playerInputSection.style.display = 'block';
            }
            if (statementSubmitted) {
                statementSubmitted.style.display = 'none';
            }
        }
    }
});

if (gameId && playerId) {

    const readyBtn = document.getElementById('readyBtn');
    if (readyBtn) {
        readyBtn.addEventListener('click', () => {
            socket.emit('player_ready', { game_id: gameId, player_id: playerId });
            readyBtn.textContent = 'Oczekiwanie na innych graczy...';
            readyBtn.disabled = true;
        });
    }

    const toggleFactionBtn = document.getElementById('toggleFactionBtn');
    const factionNameSpan = document.getElementById('factionName');
    const factionObjectivesSection = document.getElementById('factionObjectivesSection');
    if (toggleFactionBtn && factionNameSpan && factionObjectivesSection) {
        toggleFactionBtn.addEventListener('click', () => {
            if (factionNameSpan.style.display === 'none') {
                factionNameSpan.style.display = 'inline';
                factionObjectivesSection.style.display = 'block';
                toggleFactionBtn.textContent = 'Ukryj Frakcję';
            } else {
                factionNameSpan.style.display = 'none';
                factionObjectivesSection.style.display = 'none';
                toggleFactionBtn.textContent = 'Pokaż Frakcję';
            }
        });
    }

    const playerStatementInput = document.getElementById('playerStatementInput'); // Re-declare for scope
    const submitStatementBtn = document.getElementById('submitStatementBtn'); // Re-declare for scope
    
    // Action Card Logic Removed
    
    let currentFactionId = null;

    function getFactionPlaceholder(factionId) {
        if (!factionId) return "Wpisz swoje oświadczenie...";
        
        // Map faction names (IDs) to specific prompts
        if (factionId === "Wysokie Kapłaństwo") {
            return "Ogłoś jakie omeny lub cuda zsyłają bogowie..."; // Prophecy & Nature
        } else if (factionId === "Gwardia Królewska") {
            return "Jakie prawo lub karę wprowadzasz w życie?"; // Law & Order
        } else if (factionId === "Syndykat Kupiecki") {
            return "Jak reaguje lud? Co szepczą na targowiskach?"; // Voice of the People
        } else {
            return "Wpisz swoje oświadczenie...";
        }
    }

    function getFactionLabel(factionId) {
         if (!factionId) return "Twoje Słowa:";
        
        if (factionId === "Wysokie Kapłaństwo") {
            return "Proroctwo i Natura:";
        } else if (factionId === "Gwardia Królewska") {
            return "Prawo i Porządek:";
        } else if (factionId === "Syndykat Kupiecki") {
            return "Głos Ludu:";
        } else {
            return "Twoje Słowa:";
        }
    }

    if (submitStatementBtn) {
        submitStatementBtn.addEventListener('click', () => {
            const statement = playerStatementInput.value;

            if (statement) {
                socket.emit('player_action', { 
                    game_id: gameId, 
                    player_id: playerId, 
                    action: 'submit_statement', 
                    statement: statement
                });
                lastSubmittedStatement = statement; 
                
                const playerInputSection = document.getElementById('playerInputSection');
                const statementSubmitted = document.getElementById('statementSubmitted');

                if(playerInputSection) playerInputSection.style.display = 'none';
                if(statementSubmitted) statementSubmitted.style.display = 'block';
            } else {
                alert("Proszę wpisać treść oświadczenia.");
            }
        });
    }

    if (nextRoundBtn) {
        nextRoundBtn.addEventListener('click', () => {
            showLoadingScreen(true);
            socket.emit('player_action', { game_id: gameId, player_id: playerId, event: 'next_round' });
            nextRoundBtn.disabled = true;
        });
    }



    socket.on('dilemma_resolved', async (data) => {
        console.log('[DEBUG] dilemma_resolved event received.');
        showLoadingScreen(true);
        if (gameArea) gameArea.style.display = 'block'; // Ensure gameArea is visible
        narrativeText.textContent = data.outcome; // Set text content
        
        try {
            await playNarration(data.outcome); // AI NARRATOR
        } catch (error) {
            console.error("Failed to play narration:", error);
        } finally {
            completeLoading(true);
        }

        if (narrativeText) narrativeText.style.setProperty('display', 'block', 'important'); // Ensure the narrative text is visible
        currentRoundSpan.textContent = data.current_round;

        if (data.global_stats) updatePlayerStatsBars(data.global_stats);

        // Update player stats with the new data from the server
        if (data.players && data.players[playerId]) {
        }

        const narrativeOutputElement = document.getElementById('narrativeOutput');
        const nextRoundBtnElement = document.getElementById('nextRoundBtn');

        if (narrativeOutputElement) narrativeOutputElement.style.setProperty('display', 'block', 'important'); // Show narrativeOutput to display the button
        if (nextRoundBtnElement) nextRoundBtnElement.style.setProperty('display', 'block', 'important'); // Show the Next Event button
        

        const dilemmaSection = document.getElementById('dilemmaSection');
        const playerStatementsSection = document.getElementById('playerStatementsSection');


        if (dilemmaSection) dilemmaSection.style.display = 'none';
        if (playerStatementsSection) playerStatementsSection.style.display = 'none';
        waitingRoom.style.display = 'none';

        console.log(`[DEBUG] dilemma_resolved: narrativeOutput.style.display AFTER: ${narrativeOutputElement ? narrativeOutputElement.style.display : 'N/A'}`);
        console.log(`[DEBUG] dilemma_resolved: nextRoundBtn.style.display AFTER: ${nextRoundBtnElement ? nextRoundBtnElement.style.display : 'N/A'}`);
    });

    socket.on('phase_change', (data) => {
        const playerStatementsSection = document.getElementById('playerStatementsSection');
        const statementVoteSection = document.getElementById('statementVoteSection');
        const dilemmaSection = document.getElementById('dilemmaSection');
        const narrativeOutput = document.getElementById('narrativeOutput');
        const nextRoundBtn = document.getElementById('nextRoundBtn');

        console.log(`[DEBUG] phase_change: Phase: ${data.phase}`);
        console.log(`[DEBUG] phase_change: playerStatementsSection.style.display BEFORE: ${playerStatementsSection ? playerStatementsSection.style.display : 'N/A'}`);
        console.log(`[DEBUG] phase_change: statementVoteSection.style.display BEFORE: ${statementVoteSection ? statementVoteSection.style.display : 'N/A'}`);
        console.log(`[DEBUG] phase_change: dilemmaSection.style.display BEFORE: ${dilemmaSection ? dilemmaSection.style.display : 'N/A'}`);
        console.log(`[DEBUG] phase_change: narrativeOutput.style.display BEFORE: ${narrativeOutput ? narrativeOutput.style.display : 'N/A'}`);
        console.log(`[DEBUG] phase_change: nextRoundBtn.style.display BEFORE: ${nextRoundBtn ? nextRoundBtn.style.display : 'N/A'}`);


        if (data.phase === 'VOTING_PHASE') {
            const statementVoteSection = document.getElementById('statementVoteSection');
            const statementVoteList = document.getElementById('statementVoteList');
            const submitVoteBtn = document.getElementById('submitVoteBtn');
            const sabotageVoteBtn = document.getElementById('sabotageVoteBtn');
            let selectedVoteTarget = null;

            // Hide other sections
            if (playerStatementsSection) playerStatementsSection.style.display = 'none';
            if (dilemmaSection) dilemmaSection.style.display = 'none';
            if (narrativeOutput) narrativeOutput.style.display = 'none';
            if (nextRoundBtn) nextRoundBtn.style.display = 'none';
            const commentPhaseSection = document.getElementById('commentPhaseSection');
            if (commentPhaseSection) commentPhaseSection.style.display = 'none';

            if (statementVoteSection) {
                statementVoteSection.style.display = 'block';
                statementVoteList.innerHTML = ''; // Clear previous statements
                if (submitVoteBtn) submitVoteBtn.style.display = 'none';
                if (sabotageVoteBtn) sabotageVoteBtn.style.display = 'none';

                for (const aPlayerId in data.statements) {
                    // Self-voting is now allowed
                    const statementData = data.statements[aPlayerId];
                    const listItem = document.createElement('li');
                    listItem.classList.add('list-group-item', 'list-group-item-action');
                    listItem.textContent = `${statementData.name}: "${statementData.statement}"`;
                    listItem.dataset.playerId = aPlayerId;
                    
                    listItem.addEventListener('click', (event) => {
                        // Highlight
                        const items = statementVoteList.querySelectorAll('.list-group-item');
                        items.forEach(el => el.classList.remove('active'));
                        event.currentTarget.classList.add('active');
                        
                        selectedVoteTarget = event.currentTarget.dataset.playerId;
                        if (submitVoteBtn) submitVoteBtn.style.display = 'block';

                        // Sabotage Logic
                        if (sabotageVoteBtn) {
                            const spiteValEl = document.getElementById('spiteVal');
                            const currentSpite = parseInt(spiteValEl ? spiteValEl.textContent : 0) || 0;
                            if (currentSpite >= 3) {
                                sabotageVoteBtn.style.display = 'block';
                            } else {
                                sabotageVoteBtn.style.display = 'none';
                            }
                        }

                        // Preview Effect
                        const effect = statementData.predicted_effect;
                        if (effect) {
                             previewPlayerStats(clientGlobalStats, effect);
                        }
                    });
                    
                    listItem.addEventListener('dblclick', (event) => {
                        const votedForPlayerId = event.currentTarget.dataset.playerId;
                        showLoadingScreen(true);
                        socket.emit('player_action', { game_id: gameId, player_id: playerId, action: 'submit_vote', voted_for_player_id: votedForPlayerId });
                        statementVoteSection.style.display = 'none';
                    });
                    
                    statementVoteList.appendChild(listItem);
                }
                
                if (submitVoteBtn) {
                    const newBtn = submitVoteBtn.cloneNode(true);
                    submitVoteBtn.parentNode.replaceChild(newBtn, submitVoteBtn);
                    
                    newBtn.addEventListener('click', () => {
                        if (selectedVoteTarget) {
                            showLoadingScreen(true);
                            socket.emit('player_action', { game_id: gameId, player_id: playerId, action: 'submit_vote', voted_for_player_id: selectedVoteTarget });
                            statementVoteSection.style.display = 'none';
                        }
                    });
                }

                if (sabotageVoteBtn) {
                    const newSabBtn = sabotageVoteBtn.cloneNode(true);
                    sabotageVoteBtn.parentNode.replaceChild(newSabBtn, sabotageVoteBtn);
                    
                    newSabBtn.addEventListener('click', () => {
                        if (selectedVoteTarget) {
                            showLoadingScreen(true);
                            socket.emit('player_action', { 
                                game_id: gameId, 
                                player_id: playerId, 
                                action: 'submit_vote', 
                                voted_for_player_id: selectedVoteTarget,
                                type: 'sabotage' 
                            });
                            statementVoteSection.style.display = 'none';
                        }
                    });
                }
            }

        } else if (data.phase === 'COMMENT_PHASE') {
            completeLoading(true);
            const commentPhaseSection = document.getElementById('commentPhaseSection');
            const playerCommentInput = document.getElementById('playerCommentInput');
            const submitCommentBtn = document.getElementById('submitCommentBtn');
            const playerStatementResultsSection = document.getElementById('playerStatementResultsSection');


            // Hide all other sections
            if (playerStatementsSection) playerStatementsSection.style.display = 'none';
            if (statementVoteSection) statementVoteSection.style.display = 'none';
            if (dilemmaSection) dilemmaSection.style.display = 'none';
            if (narrativeOutput) narrativeOutput.style.display = 'none';
            if (nextRoundBtn) nextRoundBtn.style.display = 'none';

            if (commentPhaseSection) {
                commentPhaseSection.style.display = 'block';
                if (playerStatementResultsSection) playerStatementResultsSection.style.display = 'none'; // Hide results during commenting
                if (submitCommentBtn) {
                    submitCommentBtn.onclick = () => { // Use onclick to prevent multiple listeners
                        const comment = playerCommentInput.value;
                        showLoadingScreen(true);
                        socket.emit('player_action', { game_id: gameId, player_id: playerId, action: 'submit_comment', comment: comment });
                        playerCommentInput.value = '';
                        commentPhaseSection.style.display = 'none'; // Hide comment section after submission
                        // Optionally show a "waiting for other players" message
                    };
                }
            } else {
                console.error('[DEBUG] commentPhaseSection not found during COMMENT_PHASE phase_change!');
            }
        }
        console.log(`[DEBUG] phase_change: playerStatementsSection.style.display AFTER: ${playerStatementsSection ? playerStatementsSection.style.display : 'N/A'}`);
        console.log(`[DEBUG] phase_change: statementVoteSection.style.display AFTER: ${statementVoteSection ? statementVoteSection.style.display : 'N/A'}`);
        console.log(`[DEBUG] phase_change: dilemmaSection.style.display AFTER: ${dilemmaSection ? dilemmaSection.style.display : 'N/A'}`);
        console.log(`[DEBUG] phase_change: narrativeOutput.style.display AFTER: ${narrativeOutput ? narrativeOutput.style.display : 'N/A'}`);
        console.log(`[DEBUG] phase_change: nextRoundBtn.style.display AFTER: ${nextRoundBtn ? nextRoundBtn.style.display : 'N/A'}`);
    });

    socket.on('game_update', (data) => {
        if (data.players) {
            // This is a name update, update the player list in the voting status
            if (data.players[playerId]) {
                playerNameSpan.textContent = data.players[playerId].name;
                
                // Update Stats
                const influenceVal = document.getElementById('influenceVal');
                const spiteVal = document.getElementById('spiteVal');
                const pStats = data.players[playerId].personal_stats;
                if (influenceVal && pStats) influenceVal.textContent = pStats.Influence;
                if (spiteVal && pStats) spiteVal.textContent = pStats.Spite;
            }
        } else if (data.player_id === playerId) {
        }
    });

    socket.on('connect', () => {
        console.log('Connected to server');
        const reconnectingIndicator = document.getElementById('reconnectingIndicator');
        if (reconnectingIndicator) {
            reconnectingIndicator.style.display = 'none';
        }
        // Re-join the game room on reconnection
        if (gameId && playerId) {
            socket.emit('join_game', { game_id: gameId, player_id: playerId });
        }
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        const reconnectingIndicator = document.getElementById('reconnectingIndicator');
        if (reconnectingIndicator) {
            reconnectingIndicator.style.display = 'block';
        }
    });

    socket.on('error', (data) => {
        alert(data.message);
    });

    socket.on('other_player_reconnected', (data) => {
        console.log('Other player reconnected:', data);
    });

    socket.on('other_player_disconnected', (data) => {
        console.log('Other player disconnected:', data);
    });

    socket.on('game_over', (data) => {
        // Hide all other game areas
        if (gameArea) gameArea.style.display = 'none';
        if (document.getElementById('hostControl')) document.getElementById('hostControl').style.display = 'none';
        if (waitingRoom) waitingRoom.style.display = 'none';

        // Show the game over screen
        const gameOverScreen = document.getElementById('gameOverScreen');
        const winnerInfo = document.getElementById('winnerInfo');

        if (data.winner) {
            winnerInfo.textContent = `${data.winner.name} osiągnął całkowitą dominację!`;
        } else if (data.reason) {
            winnerInfo.textContent = data.reason;
        } else {
            winnerInfo.textContent = 'Gra się zakończyła.';
        }
        gameOverScreen.style.display = 'block';
    });

    socket.on('game_state_sync', (game_state) => {
        console.log('[DEBUG] game_state_sync received:', game_state);
        const reconnectingIndicator = document.getElementById('reconnectingIndicator');
        if (reconnectingIndicator) {
            reconnectingIndicator.style.display = 'none';
        }

        // Update global stats
        if (game_state.global_stats) {
            updatePlayerStatsBars(game_state.global_stats);
            const globalStats = game_state.global_stats;
            if (hostStatStability) {
                hostStatStability.style.width = `${globalStats.Stability}%`;
                hostStatStability.setAttribute('aria-valuenow', globalStats.Stability);
                hostStatStability.textContent = `${globalStats.Stability}`;
            }
            if (hostStatEconomy) {
                hostStatEconomy.style.width = `${globalStats.Economy}%`;
                hostStatEconomy.setAttribute('aria-valuenow', globalStats.Economy);
                hostStatEconomy.textContent = `${globalStats.Economy}`;
            }
            if (hostStatFaith) {
                hostStatFaith.style.width = `${globalStats.Faith}%`;
                hostStatFaith.setAttribute('aria-valuenow', globalStats.Faith);
                hostStatFaith.textContent = `${globalStats.Faith}`;
            }
        }

        // Update player-specific info
        if (game_state.players && game_state.players[playerId]) {
            const player = game_state.players[playerId];
            if (playerNameSpan) playerNameSpan.textContent = player.name;
            currentFactionId = player.faction; // Sync faction ID

             // Apply Asymmetric UI
            const labelElement = document.querySelector('label[for="playerStatementInput"]');
            if (playerStatementInput && getFactionPlaceholder) playerStatementInput.placeholder = getFactionPlaceholder(currentFactionId);
            if (labelElement && getFactionLabel) labelElement.textContent = getFactionLabel(currentFactionId);
            
            // Update Stats
            const influenceVal = document.getElementById('influenceVal');
            const spiteVal = document.getElementById('spiteVal');
            if (influenceVal && player.personal_stats) influenceVal.textContent = player.personal_stats.Influence;
            if (spiteVal && player.personal_stats) spiteVal.textContent = player.personal_stats.Spite;

            // Update faction name
            const factionNameSpan = document.getElementById('factionName');
            if (factionNameSpan && player.faction) {
                factionNameSpan.textContent = `Frakcja: ${player.faction}`;
            }

            // Update faction objectives
            console.log("Updating faction objectives for player");
            const factionObjectivesSection = document.getElementById('factionObjectivesSection');
            const factionObjectiveList = document.getElementById('factionObjectiveList');
            console.log("factionObjectivesSection:", factionObjectivesSection);
            console.log("factionObjectiveList:", factionObjectiveList);
            console.log("player.faction:", player.faction);
            console.log("game_state.factions:", game_state.factions);

            if (factionObjectivesSection && factionObjectiveList && player.faction && game_state.factions[player.faction]) {
                console.log("All conditions met, rendering objectives");
                factionObjectiveList.innerHTML = ''; // Clear previous objectives

                const factionData = game_state.factions[player.faction];
                let activeObjectiveFound = false;
                factionData.objectives.forEach(objective => {
                    const listItem = document.createElement('li');
                    listItem.classList.add('list-group-item');
                    if (objective.completed) {
                        listItem.innerHTML = `<del>${objective.description}</del>`;
                        factionObjectiveList.appendChild(listItem);
                    } else if (!activeObjectiveFound) {
                        listItem.textContent = objective.description;
                        factionObjectiveList.appendChild(listItem);
                        activeObjectiveFound = true;
                    }
                });
            }
            
            // Populate Target Dropdown (Update)
            const targetPlayerSelect = document.getElementById('targetPlayerSelect');
            if (targetPlayerSelect) {
                 // Save current selection if any
                 const currentSelection = targetPlayerSelect.value;
                 targetPlayerSelect.innerHTML = '';
                 for (const pid in game_state.players) {
                    if (pid !== playerId && game_state.players[pid].action_status !== 'empty') {
                        const option = document.createElement('option');
                        option.value = pid;
                        option.textContent = game_state.players[pid].name;
                        targetPlayerSelect.appendChild(option);
                    }
                }
                if (currentSelection) {
                    targetPlayerSelect.value = currentSelection;
                }
            }
        }
        if (currentRoundSpan) currentRoundSpan.textContent = game_state.current_round;

        // Adjust UI based on game state
        const hostControl = document.getElementById('hostControl');
        const gameSetup = document.getElementById('gameSetup');
        const lobbyControl = document.getElementById('lobbyControl');
        const dilemmaSection = document.getElementById('dilemmaSection');
        const playerStatementsSection = document.getElementById('playerStatementsSection');
        const statementVoteSection = document.getElementById('statementVoteSection');
        const commentPhaseSection = document.getElementById('commentPhaseSection');
        const narrativeOutput = document.getElementById('narrativeOutput');
        const nextRoundBtn = document.getElementById('nextRoundBtn');
        const waitingRoom = document.getElementById('waitingRoom');
        const gameOverScreen = document.getElementById('gameOverScreen');
        const mainContentArea = document.getElementById('mainContentArea');


        // Hide all main game sections initially
        if (gameSetup) gameSetup.style.display = 'none';
        if (lobbyControl) lobbyControl.style.display = 'none';
        if (hostControl) hostControl.style.display = 'none';
        if (gameArea) gameArea.style.display = 'none';
        if (dilemmaSection) dilemmaSection.style.display = 'none';
        if (playerStatementsSection) playerStatementsSection.style.display = 'none';
        if (statementVoteSection) statementVoteSection.style.display = 'none';
        if (commentPhaseSection) commentPhaseSection.style.display = 'none';
        if (narrativeOutput) narrativeOutput.style.display = 'none';
        if (nextRoundBtn) nextRoundBtn.style.display = 'none';
        if (waitingRoom) waitingRoom.style.display = 'none';
        if (gameOverScreen) gameOverScreen.style.display = 'none';
        if (mainContentArea) mainContentArea.style.display = 'none';


        // Show relevant sections based on game state
        if (game_state.state === 'waiting') {
            if (gameArea) gameArea.style.display = 'block';
            if (waitingRoom) waitingRoom.style.display = 'block';
        } else if (game_state.state === 'DILEMMA') {
            if (gameArea) gameArea.style.display = 'block';
            if (mainContentArea) mainContentArea.style.display = 'block';
            if (dilemmaSection) dilemmaSection.style.display = 'block';
            if (playerStatementsSection) playerStatementsSection.style.display = 'block';
            if (game_state.current_dilemma) {
                dilemmaTitle.textContent = game_state.current_dilemma.title;
                dilemmaDescription.textContent = game_state.current_dilemma.description;
            }
        } else if (game_state.state === 'COMMENT_PHASE') {
            if (gameArea) gameArea.style.display = 'block';
            if (mainContentArea) mainContentArea.style.display = 'block';
            if (commentPhaseSection) commentPhaseSection.style.display = 'block';
            // Potentially re-render statements for voting if that's part of the comment phase UI
        } else if (game_state.state === 'OUTCOME_DISPLAYED') {
            if (gameArea) gameArea.style.display = 'block';
            if (mainContentArea) mainContentArea.style.display = 'block';
            if (narrativeOutput) narrativeOutput.style.display = 'block';
            if (nextRoundBtn) nextRoundBtn.style.display = 'block';
            if (game_state.last_outcome_narrative_data && narrativeText) {
                narrativeText.textContent = game_state.last_outcome_narrative_data.outcome_narrative;
            }
        } else if (game_state.state === 'GAME_OVER') {
            if (gameOverScreen) gameOverScreen.style.display = 'block';
            // Populate winner info if available
        }

        // Host specific UI updates
        if (document.getElementById('hostControl')) {
            if (hostControl) hostControl.style.display = 'block';
            
            updateHostFactionObjectives(game_state.factions);
        }
    });
}
function updatePlayerStatusOnHost(player, playerId) {
    const playerStatus = document.getElementById(`player-status-${playerId}`);
    if (playerStatus) {
        let statusText = player.name;

        playerStatus.innerHTML = ''; // Clear existing content

        const nameSpan = document.createElement('span');
        nameSpan.textContent = statusText;
        playerStatus.appendChild(nameSpan);

        playerStatus.classList.remove('player-name-glow', 'player-dots-glow', 'player-dots-yellow', 'player-name-yellow', 'player-joined'); // Remove previous states
        nameSpan.classList.remove('player-name-glow', 'player-name-yellow'); // Remove from nameSpan as well

        if (player.action_status === 'empty') {
            // No special glow for empty slots, just display the name (e.g., "Player 1 (Empty)")
        } else if (player.action_status === 'joined') {
            playerStatus.classList.add('player-joined');
        } else if (player.action_status === 'waiting') {
            const dotsSpan = document.createElement('span');
            dotsSpan.classList.add('player-dots-glow'); // Original glowing dots for waiting in-game
            dotsSpan.textContent = ' ● ● ●';
            playerStatus.appendChild(dotsSpan);
        } else if (player.action_status === 'done') {
            nameSpan.classList.add('player-name-glow'); // Original glowing name for action done
        }

        if (player.ready) {
            nameSpan.classList.add('player-name-yellow'); // Glowing yellow name for ready players
        }
    }
}

// For the host page (index.html)
const createGameBtn = document.getElementById('createGameBtn');
const backgroundMusic = document.getElementById('backgroundMusic');

if (backgroundMusic) {
    backgroundMusic.volume = 0.05; // Set volume to a quiet level
}

if (createGameBtn) {
    createGameBtn.addEventListener('click', () => {
        const numPlayers = document.getElementById('numPlayers').value;
        socket.emit('create_game', { num_players: parseInt(numPlayers) });
        if (backgroundMusic) {
            backgroundMusic.play().catch(e => console.error("Error playing background music:", e));
        }
    });

    socket.on('game_created', (data) => {
        document.getElementById('gameIdDisplay').textContent = data.game_id;
        const joinQrCodeDiv = document.getElementById('joinQrCode');
        joinQrCodeDiv.innerHTML = ''; // Clear existing content

        const url = new URL(data.join_url, window.location.origin).href;
        const qr = qrcode(0, 'L');
        qr.addData(url);
        qr.make();
        joinQrCodeDiv.innerHTML = qr.createImgTag(6); // Larger QR code

        const playerStatusDiv = document.getElementById('playerStatus');
        playerStatusDiv.innerHTML = '';
        for (const playerId in data.players) {
            const player = data.players[playerId];
            const playerItem = document.createElement('div');
            playerItem.classList.add('list-group-item');
            playerItem.id = `player-status-${playerId}`;
            playerStatusDiv.appendChild(playerItem);
            updatePlayerStatusOnHost(player, playerId);
        }
        
        document.getElementById('gameSetup').style.display = 'none';
        document.getElementById('lobbyControl').style.display = 'block';
    });

    socket.on('player_joined', (players) => {
        for (const pid in players) {
            const playerItem = document.getElementById(`player-status-${pid}`);
            if (playerItem && !playerItem.classList.contains('player-joining')) { // Only animate if not already animating
                playerItem.classList.add('player-joining');
                setTimeout(() => {
                    playerItem.classList.remove('player-joining');
                }, 500); // Animation duration
            }
            updatePlayerStatusOnHost(players[pid], pid);
        }
    });

    socket.on('player_ready_update', (data) => {
        updatePlayerStatusOnHost(data.player, data.player_id);
    });

    socket.on('player_disconnected', (data) => {
        updatePlayerStatusOnHost(data.player, data.player_id);
    });

    socket.on('game_update', (data) => {
        if (data.players) {
            // This is a name update or choice update, update the player list on the host page
            for (const pid in data.players) {
                updatePlayerStatusOnHost(data.players[pid], pid);
            }
            // Removed votingStatus update as it's now integrated into updatePlayerStatusOnHost
        } else {
            // This is for host to see player specific updates, e.g., faction assignment
            console.log('Host received game_update:', data);
        }
    });

    socket.on('dilemma_resolved', (data) => {
        // Update host global stats progress bars
        const globalStats = data.global_stats;
        hostStatStability.style.width = `${globalStats.Stability}%`;
        hostStatStability.setAttribute('aria-valuenow', globalStats.Stability);
        hostStatStability.textContent = `${globalStats.Stability}`;

        hostStatEconomy.style.width = `${globalStats.Economy}%`;
        hostStatEconomy.setAttribute('aria-valuenow', globalStats.Economy);
        hostStatEconomy.textContent = `${globalStats.Economy}`;

        hostStatFaith.style.width = `${globalStats.Faith}%`;
        hostStatFaith.setAttribute('aria-valuenow', globalStats.Faith);
        hostStatFaith.textContent = `${globalStats.Faith}`;

        // The narrative and statement voting results are now handled by comments_received and phase_change events
        // Ensure the narrative is hidden until comments_received
        const hostNarrative = document.getElementById('hostNarrative');
        // if (hostNarrative) hostNarrative.style.display = 'none'; // This line is removed
    });

    socket.on('phase_change', (data) => {
        // Host-specific phase change handling
        const hostNarrative = document.getElementById('hostNarrative');
        const statementVotingResultsDisplay = document.getElementById('statementVotingResultsDisplay');
        const playerCommentsDisplay = document.getElementById('playerCommentsDisplay');

        if (data.phase === 'DISPLAY_STATEMENT_RESULTS') {
            if (statementVotingResultsDisplay && data.statement_vote_counts && data.players) {
                statementVotingResultsDisplay.style.display = 'block';
                const statementVoteCountsDiv = document.getElementById('statementVoteCounts');
                statementVoteCountsDiv.innerHTML = '<h6>Rozkład Głosów na Oświadczenia:</h6>';
                const statementVoteList = document.createElement('ul');
                statementVoteList.classList.add('list-group');

                // Map player IDs to their names and statements for easier display
                const playerInfo = {};
                for (const pid in data.players) {
                    playerInfo[pid] = {
                        name: data.players[pid].name,
                        statement: data.players[pid].statement || 'Brak oświadczenia'
                    };
                }

                for (const pid in data.statement_vote_counts) {
                    const votes = data.statement_vote_counts[pid];
                    const listItem = document.createElement('li');
                    listItem.classList.add('list-group-item');
                    let statementText = `${playerInfo[pid].name}: "${playerInfo[pid].statement}" - ${votes} głosów`;
                    listItem.innerHTML = statementText;
                    statementVoteList.appendChild(listItem);
                }
                statementVoteCountsDiv.appendChild(statementVoteList);

                // Hide narrative and comments sections
                if (hostNarrative) hostNarrative.style.display = 'none';
                if (playerCommentsDisplay) playerCommentsDisplay.style.display = 'none';
            }
        } else if (data.phase === 'COMMENT_PHASE') {
            // During comment phase, host should still see statement results
            if (statementVotingResultsDisplay) statementVotingResultsDisplay.style.display = 'block';
            if (playerCommentsDisplay) playerCommentsDisplay.style.display = 'none'; // Hide comments until received
            if (hostNarrative) hostNarrative.style.display = 'none'; // Hide narrative until comments received
        }
    });

    socket.on('comments_received', async (data) => {
        console.log('Comments received event fired');
        console.log('Comments received:', data);
        showLoadingScreen(false);
        const playerCommentsDisplay = document.getElementById('playerCommentsDisplay');
        const commentList = document.getElementById('commentList');
        const hostNarrative = document.getElementById('hostNarrative');
        const statementVotingResultsDisplay = document.getElementById('statementVotingResultsDisplay');
        const playerStatementsDiv = document.getElementById('playerStatements'); // Get the player statements div

        if (playerCommentsDisplay && commentList && data.comments) {
            if (statementVotingResultsDisplay) statementVotingResultsDisplay.style.display = 'none'; // Hide statement voting results
            if (playerStatementsDiv) playerStatementsDiv.style.display = 'none'; // Hide player statements
            playerCommentsDisplay.style.display = 'block'; // Show comments section
            commentList.innerHTML = ''; // Clear and add a title

            for (const pid in data.comments) {
                const commentData = data.comments[pid];
                const listItem = document.createElement('li');
                listItem.classList.add('list-group-item');
                listItem.textContent = `${commentData.name}: "${commentData.comment}"`;
                commentList.appendChild(listItem);
            }

            // Now display the outcome narrative
            if (hostNarrative) {
                hostNarrative.textContent = data.outcome; // Assuming outcome is passed in data
                hostNarrative.style.display = 'block';
                try {
                    await playNarration(data.outcome); // AI NARRATOR
                } catch (error) {
                    console.error("Failed to play narration:", error);
                } finally {
                    completeLoading(false);
                }
            }
        }
    });

    let all_statements = {};
    socket.on('statements_submitted', (data) => {
        all_statements = data.statements;
        console.log('Statements submitted:', data);
        const playerStatementsDiv = document.getElementById('playerStatements');
        const playerStatementList = document.getElementById('playerStatementList');

        if (playerStatementsDiv && playerStatementList) {
            playerStatementList.innerHTML = ''; // Clear previous statements
            for (const playerId in data.statements) {
                const statementData = data.statements[playerId];
                const listItem = document.createElement('li');
                listItem.classList.add('list-group-item');
                listItem.textContent = `${statementData.name}: "${statementData.statement}"`;
                playerStatementList.appendChild(listItem);
            }
            playerStatementsDiv.style.display = 'block'; // Show the statements section
        }
        // Hide hostNarrative if it was showing the dilemma description
        const hostNarrative = document.getElementById('hostNarrative');
        if (hostNarrative) hostNarrative.style.display = 'none';
    });

    socket.on('voting_results', (data) => {
        const statementVotingResultsDisplay = document.getElementById('statementVotingResultsDisplay');
        const statementVoteCounts = document.getElementById('statementVoteCounts');

        if (statementVotingResultsDisplay && statementVoteCounts) {
            statementVotingResultsDisplay.style.display = 'block';
            statementVoteCounts.innerHTML = ''; // Clear previous results

            const voteList = document.createElement('ul');
            voteList.classList.add('list-group');

            for (const playerId in data.vote_counts) {
                const voteCount = data.vote_counts[playerId];
                const statementData = all_statements[playerId];
                                    const statementText = `${statementData.statement}`; // Changed this line
                const listItem = document.createElement('li');
                listItem.classList.add('list-group-item');
                listItem.innerHTML = `${statementText} - ${voteCount} głosów`;
                if (data.winning_statement.player_id === playerId) {
                    listItem.classList.add('list-group-item-success');
                }
                voteList.appendChild(listItem);
            }
            statementVoteCounts.appendChild(voteList);
        }
        const playerStatementsDiv = document.getElementById('playerStatements');
        if (playerStatementsDiv) playerStatementsDiv.style.display = 'none'; // Hide player statements
    });
}
function updatePlayerStatsBars(globalStats) {
    // Update local cache
    clientGlobalStats = { ...globalStats };

    const stabBar = document.getElementById('playerStatStability');
    const econBar = document.getElementById('playerStatEconomy');
    const faithBar = document.getElementById('playerStatFaith');
    
    const valStab = document.getElementById('valStability');
    const valEcon = document.getElementById('valEconomy');
    const valFaith = document.getElementById('valFaith');

    if (stabBar) stabBar.style.width = `${globalStats.Stability}%`;
    if (econBar) econBar.style.width = `${globalStats.Economy}%`;
    if (faithBar) faithBar.style.width = `${globalStats.Faith}%`;

    if (valStab) valStab.textContent = globalStats.Stability;
    if (valEcon) valEcon.textContent = globalStats.Economy;
    if (valFaith) valFaith.textContent = globalStats.Faith;
}

function previewPlayerStats(baseStats, effect) {
    if (!effect) effect = { Stability: 0, Economy: 0, Faith: 0 };

    const updateStat = (barId, textId, base, change) => {
        const bar = document.getElementById(barId);
        const text = document.getElementById(textId);
        
        let newValue = base + (change || 0);
        newValue = Math.max(0, Math.min(100, newValue)); // Clamp

        if (bar) {
            bar.style.width = `${newValue}%`;
            // Add a transition effect via JS or rely on CSS
            bar.style.transition = "width 0.3s ease-in-out"; 
        }

        if (text) {
            if (change && change !== 0) {
                const sign = change > 0 ? '+' : '';
                text.textContent = `${base} (${sign}${change})`;
                text.style.color = change > 0 ? '#5cb85c' : '#d9534f'; // Green or Red
            } else {
                text.textContent = base;
                text.style.color = 'white';
            }
        }
    };

    updateStat('playerStatStability', 'valStability', baseStats.Stability, effect.Stability);
    updateStat('playerStatEconomy', 'valEconomy', baseStats.Economy, effect.Economy);
    updateStat('playerStatFaith', 'valFaith', baseStats.Faith, effect.Faith);
}

