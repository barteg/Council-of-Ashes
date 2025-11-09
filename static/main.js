const socket = io('http://10.0.1.38:5000');

const gameId = document.getElementById('gameId') ? document.getElementById('gameId').textContent.trim() : null;
const playerId = document.getElementById('playerId') ? document.getElementById('playerId').textContent.trim() : null;

const waitingRoom = document.getElementById('waitingRoom');
const gameArea = document.getElementById('gameArea');
const nameSetup = document.getElementById('nameSetup');
const factionSelection = document.getElementById('factionSelection');

const playerNameSpan = document.getElementById('playerName');
const currentRoundSpan = document.getElementById('currentRound');
const statInfluenceSpan = document.getElementById('statInfluence');

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

function updatePersonalStats(playerData) {
    if (playerData && playerData.personal_stats) {
        const influence = playerData.personal_stats.Influence;
        if (statInfluenceSpan) {
            statInfluenceSpan.style.width = `${influence}%`;
            statInfluenceSpan.setAttribute('aria-valuenow', influence);
            statInfluenceSpan.textContent = `${influence}`; // Display number inside bar
        }
    }
}

function updatePlayerChoiceStatus(players) {
    const playerChoiceList = document.getElementById('playerChoiceList');
    if (playerChoiceList) {
        playerChoiceList.innerHTML = '';
        for (const pid in players) {
            const player = players[pid];
            const listItem = document.createElement('li');
            listItem.classList.add('list-group-item');
            listItem.textContent = `${player.name}: ${player.choice !== null ? 'Chosen' : 'Waiting...'}`;
            playerChoiceList.appendChild(listItem);
        }
        const votingStatus = document.getElementById('votingStatus');
        if(votingStatus) {
            // votingStatus.style.display = 'block';
        }
    }
}

if (nextRoundBtn) {
    nextRoundBtn.addEventListener('click', () => {
        socket.emit('player_action', { game_id: gameId, player_id: playerId, event: 'next_round' });
        nextRoundBtn.disabled = true;
    });
}

// This listener is now global to be heard by the host
socket.on('game_started_for_player', (initial_game_state) => {
    console.log('[DEBUG] game_started_for_player event received');
    const hostControl = document.getElementById('hostControl');

    if (hostControl) { // hostGameArea is removed, so we only check for hostControl
        // Host
        console.log('[DEBUG] Client is host, updating UI');
        document.getElementById('gameSetup').style.display = 'none'; // Explicitly hide gameSetup
        console.log('[DEBUG] hostControl initial display style:', hostControl.style.display); // Add this line
        hostControl.style.display = 'block'; // Ensure hostControl is visible
        console.log('[DEBUG] hostControl display style after setting:', hostControl.style.display); // Modify this line

        // Now, make the game-specific elements within hostControl visible
        document.getElementById('factionColumns').style.display = 'flex'; // Assuming it's a flex container
        document.getElementById('hostStatStability').parentElement.parentElement.style.display = 'block'; // Parent of progress bar
        document.getElementById('hostStatEconomy').parentElement.parentElement.style.display = 'block';
        document.getElementById('hostStatFaith').parentElement.parentElement.style.display = 'block';
        document.getElementById('hostNarrative').parentElement.style.display = 'block'; // Parent of narrative
        document.getElementById('hostNarrative').style.display = 'block'; // Make the narrative text itself visible

        // Hide all lobby-specific elements
        document.getElementById('gameControlContainer').style.display = 'none';
    } else if (gameArea) {
        // Player
        waitingRoom.style.display = 'none';
        gameArea.style.display = 'block';
        console.log(`[DEBUG] game_started_for_player: gameArea.style.display after setting: ${gameArea.style.display}`);

        // Initial update of player-specific stats and faction
        if (initial_game_state && initial_game_state.players && initial_game_state.players[playerId]) {
            playerNameSpan.textContent = initial_game_state.players[playerId].name;
            updatePersonalStats(initial_game_state.players[playerId]);
        }
    }
});

socket.on('game_event', (data) => {
    console.log('Game Event:', data);
    if (data.event === 'dilemma_prompt') {
        const dilemma = JSON.parse(data.dilemma_json);

        // Check if we are on the host page
        if (document.getElementById('hostControl')) {
            console.log('[DEBUG] Host Dilemma Description:', dilemma.description);
            document.getElementById('hostNarrative').textContent = dilemma.description;
            // Update host global stats progress bars
            const globalStats = data.global_stats;
            console.log('[DEBUG] Host Global Stats:', globalStats); // Add this line
            if (globalStats) {
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
        }

        // Check if we are on the player page
        if (document.getElementById('gameArea')) {
            console.log('[DEBUG] Player Dilemma Object:', dilemma);
            dilemmaTitle.textContent = dilemma.title;

            // Update current kingdom stats display
            const globalStats = data.global_stats;
            const currentStatStability = document.getElementById('currentStatStability');
            const currentStatEconomy = document.getElementById('currentStatEconomy');
            const currentStatFaith = document.getElementById('currentStatFaith');

            if (currentStatStability) {
                currentStatStability.style.width = `${globalStats.Stability}%`;
                currentStatStability.setAttribute('aria-valuenow', globalStats.Stability);
                currentStatStability.textContent = `${globalStats.Stability}`;
            }
            if (currentStatEconomy) {
                currentStatEconomy.style.width = `${globalStats.Economy}%`;
                currentStatEconomy.setAttribute('aria-valuenow', globalStats.Economy);
                currentStatEconomy.textContent = `${globalStats.Economy}`;
            }
            if (currentStatFaith) {
                currentStatFaith.style.width = `${globalStats.Faith}%`;
                currentStatFaith.setAttribute('aria-valuenow', globalStats.Faith);
                currentStatFaith.textContent = `${globalStats.Faith}`;
            }

            const dilemmaChoices = document.getElementById('dilemmaChoices'); // Select element just-in-time
            const dilemmaSection = document.getElementById('dilemmaSection');
            const playerStatementsSection = document.getElementById('playerStatementsSection');
            const statementVoteSection = document.getElementById('statementVoteSection');


            console.log(`[DEBUG] dilemma_prompt: gameArea.style.display: ${gameArea.style.display}`);
            console.log(`[DEBUG] dilemma_prompt: dilemmaSection.style.display BEFORE: ${dilemmaSection ? dilemmaSection.style.display : 'N/A'}`);
            console.log(`[DEBUG] dilemma_prompt: playerStatementsSection.style.display BEFORE: ${playerStatementsSection ? playerStatementsSection.style.display : 'N/A'}`);
            console.log(`[DEBUG] dilemma_prompt: statementVoteSection.style.display BEFORE: ${statementVoteSection ? statementVoteSection.style.display : 'N/A'}`);


            if (!dilemmaChoices) {
                console.error('Could not find dilemmaChoices element!');
                return; 
            }

            const originalStats = {
                Stability: globalStats.Stability,
                Economy: globalStats.Economy,
                Faith: globalStats.Faith
            };

            dilemmaChoices.innerHTML = '';
            dilemma.choices.forEach((choice, index) => {
                console.log('[DEBUG] Rendering choice:', choice.text); // Add this line
                const button = document.createElement('button');
                button.classList.add('list-group-item', 'list-group-item-action', 'mb-2');
                let buttonText = choice.text;
                const effects = [];
                if (choice.effects.Stability !== 0) {
                    effects.push(`${choice.effects.Stability > 0 ? '+' : ''}${choice.effects.Stability} Stability`);
                }
                if (choice.effects.Economy !== 0) {
                    effects.push(`${choice.effects.Economy > 0 ? '+' : ''}${choice.effects.Economy} Economy`);
                }
                if (choice.effects.Faith !== 0) {
                    effects.push(`${choice.effects.Faith > 0 ? '+' : ''}${choice.effects.Faith} Faith`);
                }
                if (effects.length > 0) {
                    buttonText += ` (${effects.join(', ')})`;
                }
                button.textContent = buttonText;
                button.addEventListener('click', () => {
                    // Remove 'active' class from all choices and add to the clicked one
                    Array.from(dilemmaChoices.children).forEach(btn => btn.classList.remove('active'));
                    button.classList.add('active');
                    playerChoice = index; // Store the choice, but don't submit yet

                    // Preview the stat changes
                    const newStability = Math.max(0, Math.min(100, originalStats.Stability + choice.effects.Stability));
                    const newEconomy = Math.max(0, Math.min(100, originalStats.Economy + choice.effects.Economy));
                    const newFaith = Math.max(0, Math.min(100, originalStats.Faith + choice.effects.Faith));

                    currentStatStability.style.width = `${newStability}%`;
                    currentStatStability.setAttribute('aria-valuenow', newStability);
                    currentStatStability.textContent = `${newStability}`;

                    currentStatEconomy.style.width = `${newEconomy}%`;
                    currentStatEconomy.setAttribute('aria-valuenow', newEconomy);
                    currentStatEconomy.textContent = `${newEconomy}`;

                    currentStatFaith.style.width = `${newFaith}%`;
                    currentStatFaith.setAttribute('aria-valuenow', newFaith);
                    currentStatFaith.textContent = `${newFaith}`;
                });

                button.addEventListener('dblclick', () => {
                    if (playerChoice === index) { // Ensure the double-clicked item is the selected one
                        
                        // Revert to original stats before submitting
                        currentStatStability.style.width = `${originalStats.Stability}%`;
                        currentStatStability.setAttribute('aria-valuenow', originalStats.Stability);
                        currentStatStability.textContent = `${originalStats.Stability}`;

                        currentStatEconomy.style.width = `${originalStats.Economy}%`;
                        currentStatEconomy.setAttribute('aria-valuenow', originalStats.Economy);
                        currentStatEconomy.textContent = `${originalStats.Economy}`;

                        currentStatFaith.style.width = `${originalStats.Faith}%`;
                        currentStatFaith.setAttribute('aria-valuenow', originalStats.Faith);
                        currentStatFaith.textContent = `${originalStats.Faith}`;

                        socket.emit('player_action', { game_id: gameId, player_id: playerId, action: 'dilemma_choice', choice: index });
                        // Disable choices after selection
                        Array.from(dilemmaChoices.children).forEach(btn => btn.disabled = true);
                        button.classList.add('active');

                        console.log(`[DEBUG] Dilemma choice dblclicked: dilemmaSection.style.display BEFORE: ${dilemmaSection ? dilemmaSection.style.display : 'N/A'}`);
                        console.log(`[DEBUG] Dilemma choice dblclicked: playerStatementsSection.style.display BEFORE: ${playerStatementsSection ? playerStatementsSection.style.display : 'N/A'}`);
                        console.log(`[DEBUG] Dilemma choice dblclicked: statementVoteSection.style.display BEFORE: ${statementVoteSection ? statementVoteSection.style.display : 'N/A'}`);


                        // Hide dilemma and show statement section
                        if (dilemmaSection) dilemmaSection.style.display = 'none';
                        if (playerStatementsSection) playerStatementsSection.style.display = 'block';
                        if (statementVoteSection) statementVoteSection.style.display = 'none';


                        console.log(`[DEBUG] Dilemma choice dblclicked: dilemmaSection.style.display AFTER: ${dilemmaSection ? dilemmaSection.style.display : 'N/A'}`);
                        console.log(`[DEBUG] Dilemma choice dblclicked: playerStatementsSection.style.display AFTER: ${playerStatementsSection ? playerStatementsSection.style.display : 'N/A'}`);
                        console.log(`[DEBUG] Dilemma choice dblclicked: statementVoteSection.style.display AFTER: ${statementVoteSection ? statementVoteSection.style.display : 'N/A'}`);
                    }
                });
                dilemmaChoices.appendChild(button);
            });
            console.log('[DEBUG] Number of dilemma choices rendered:', dilemmaChoices.children.length); // Add this line

            const currentRoundSpan = document.getElementById('currentRound');
            if (currentRoundSpan) {
                currentRoundSpan.textContent = data.current_round;
            }
            // Re-enable choices
            // const dilemmaChoices = document.getElementById('dilemmaChoices'); // This was a duplicate declaration
            if (dilemmaChoices) {
                Array.from(dilemmaChoices.children).forEach(btn => btn.disabled = false);
                Array.from(dilemmaChoices.children).forEach(btn => btn.classList.remove('active'));
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
                playerStatementsSection.style.display = 'none';
                console.log(`[DEBUG] dilemma_prompt: playerStatementsSection.style.display after setting: ${playerStatementsSection.style.display}`);
            }
            if (statementVoteSection) { // Ensure statementVoteSection is initially hidden
                statementVoteSection.style.display = 'none';
                console.log(`[DEBUG] dilemma_prompt: statementVoteSection.style.display after setting: ${statementVoteSection.style.display}`);
            }
            waitingRoom.style.display = 'none';
            if(nextRoundBtn) {
                nextRoundBtn.disabled = false;
            }
        }
    } else if (data.event === 'player_made_choice' || data.event === 'other_player_made_choice') {
        // Request updated player choices from server to update status
        // For now, we'll just show a generic message
        // Removed votingStatus reference
        // In a more complete implementation, you'd request the full player list to update playerChoiceList
    }
});

if (gameId && playerId) {

    const saveNameBtn = document.getElementById('saveNameBtn');
    if (saveNameBtn) {
        saveNameBtn.addEventListener('click', () => {
            const newName = document.getElementById('playerNameInput').value;
            if (newName) {
                socket.emit('player_name_update', { game_id: gameId, player_id: playerId, name: newName });
                nameSetup.style.display = 'none';
                factionSelection.style.display = 'block';
            }
        });
    }

    const readyBtn = document.getElementById('readyBtn');
    if (readyBtn) {
        readyBtn.addEventListener('click', () => {
            socket.emit('player_ready', { game_id: gameId, player_id: playerId });
            readyBtn.textContent = 'Waiting for other players...';
            readyBtn.disabled = true;
        });
    }

    const playerStatementInput = document.getElementById('playerStatementInput'); // Re-declare for scope
    const submitStatementBtn = document.getElementById('submitStatementBtn'); // Re-declare for scope
    if (submitStatementBtn) {
        submitStatementBtn.addEventListener('click', () => {
            const statement = playerStatementInput.value;
            if (statement) {
                socket.emit('player_action', { game_id: gameId, player_id: playerId, action: 'submit_statement', statement: statement });
                playerStatementInput.value = '';
                // Maybe show a confirmation
            }
        });
    }

    if (nextRoundBtn) {
        nextRoundBtn.addEventListener('click', () => {
            socket.emit('player_action', { game_id: gameId, player_id: playerId, event: 'next_round' });
            nextRoundBtn.disabled = true;
        });
    }

    socket.on('faction_info', (data) => {
        const factionSelectionDiv = document.getElementById('factionSelection');
        const factionSelect = document.getElementById('factionSelect');
        factionSelect.innerHTML = '';

        for (const factionId in data.factions) {
            const option = document.createElement('option');
            option.value = factionId;
            option.textContent = factionId;
            factionSelect.appendChild(option);
        }
        
        const joinFactionBtn = document.getElementById('joinFactionBtn');
        joinFactionBtn.addEventListener('click', () => {
            const selectedFaction = factionSelect.value;
            if (selectedFaction) {
                socket.emit('join_faction', { game_id: gameId, player_id: playerId, faction_id: selectedFaction });
                factionSelectionDiv.style.display = 'none';
                waitingRoom.style.display = 'block';
            }
        });

        // This was moved to after name save
        // factionSelectionDiv.style.display = 'block';
        // waitingRoom.style.display = 'none';
    });



    socket.on('dilemma_resolved', (data) => {
        console.log('[DEBUG] dilemma_resolved event received.');
        if (gameArea) gameArea.style.display = 'block'; // Ensure gameArea is visible
        narrativeText.textContent = data.outcome; // Set text content
        if (narrativeText) narrativeText.style.setProperty('display', 'block', 'important'); // Ensure the narrative text is visible
        currentRoundSpan.textContent = data.current_round;

        // Update player stats with the new data from the server
        if (data.players && data.players[playerId]) {
            updatePersonalStats(data.players[playerId]);
        }

        const narrativeOutputElement = document.getElementById('narrativeOutput');
        const nextRoundBtnElement = document.getElementById('nextRoundBtn');

        if (narrativeOutputElement) narrativeOutputElement.style.setProperty('display', 'block', 'important'); // Show narrativeOutput to display the button
        if (nextRoundBtnElement) nextRoundBtnElement.style.setProperty('display', 'block', 'important'); // Show the Next Event button
        

        const dilemmaSection = document.getElementById('dilemmaSection');
        const playerStatementsSection = document.getElementById('playerStatementsSection');
        const statementVoteSection = document.getElementById('statementVoteSection');


        if (dilemmaSection) dilemmaSection.style.display = 'none';
        if (playerStatementsSection) playerStatementsSection.style.display = 'none';
        if (statementVoteSection) statementVoteSection.style.display = 'none';
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


        if (data.phase === 'STATEMENT_VOTE') {
            if (playerStatementsSection) playerStatementsSection.style.display = 'none'; // Hide statement submission
            if (dilemmaSection) dilemmaSection.style.display = 'none'; // Hide dilemma section
            if (narrativeOutput) narrativeOutput.style.display = 'none'; // Hide narrative output
            if (nextRoundBtn) nextRoundBtn.style.display = 'none'; // Hide next round button
            
            if (statementVoteSection) {
                const statementVoteList = document.getElementById('statementVoteList');
                statementVoteList.innerHTML = '';

                for (const pid in data.statements) {
                    const statementData = data.statements[pid];
                    const listItem = document.createElement('li');
                    listItem.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center');
                    listItem.textContent = `${statementData.name}: "${statementData.statement}"`;

                    const voteButton = document.createElement('button');
                    voteButton.classList.add('btn', 'btn-sm', 'btn-primary');
                    voteButton.textContent = 'Vote';
                    voteButton.addEventListener('click', () => {
                        socket.emit('player_action', { game_id: gameId, player_id: playerId, action: 'submit_statement_vote', vote_for_player_id: pid });
                        // Hide the entire voting section after selection
                        if (statementVoteSection) statementVoteSection.style.display = 'none';
                        console.log('[DEBUG] Vote button clicked. statementVoteSection hidden.');
                    });
                    listItem.appendChild(voteButton);
                    statementVoteList.appendChild(listItem);
                }
                statementVoteSection.style.display = 'block'; // Show voting section
            } else {
                console.error('[DEBUG] statementVoteSection not found during STATEMENT_VOTE phase_change!');
            }
        } else if (data.phase === 'DISPLAY_STATEMENT_RESULTS') {
            // Hide all other sections
            if (playerStatementsSection) playerStatementsSection.style.display = 'none';
            if (statementVoteSection) statementVoteSection.style.display = 'none';
            if (dilemmaSection) dilemmaSection.style.display = 'none';
            if (narrativeOutput) narrativeOutput.style.display = 'none';
            if (nextRoundBtn) nextRoundBtn.style.display = 'none';

            // Display statement voting results on player screen (if needed, currently only host)
            // For players, this phase is mostly a transition before commenting
            const playerStatementResultsSection = document.getElementById('playerStatementResultsSection');
            if (playerStatementResultsSection) {
                playerStatementResultsSection.style.display = 'block';
                const statementResultsList = document.getElementById('statementResultsList');
                statementResultsList.innerHTML = '<h6>Statement Vote Distribution:</h6>';
                const statementVoteList = document.createElement('ul');
                statementVoteList.classList.add('list-group');

                const playerInfo = {};
                for (const pid in data.players) {
                    playerInfo[pid] = {
                        name: data.players[pid].name,
                        statement: data.players[pid].statement || 'No statement submitted'
                    };
                }

                for (const pid in data.statement_vote_counts) {
                    const votes = data.statement_vote_counts[pid];
                    const listItem = document.createElement('li');
                    listItem.classList.add('list-group-item');
                    let statementText = `${playerInfo[pid].name}: "${playerInfo[pid].statement}" - ${votes} votes`;
                    listItem.innerHTML = statementText;
                    statementVoteList.appendChild(listItem);
                }
                statementResultsList.appendChild(statementVoteList);
            }

        } else if (data.phase === 'COMMENT_PHASE') {
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
                if (playerStatementResultsSection) playerStatementResultsSection.style.display = 'block'; // Keep results visible during commenting
                if (submitCommentBtn) {
                    submitCommentBtn.onclick = () => { // Use onclick to prevent multiple listeners
                        const comment = playerCommentInput.value;
                        if (comment) {
                            socket.emit('player_action', { game_id: gameId, player_id: playerId, action: 'submit_comment', comment: comment });
                            playerCommentInput.value = '';
                            commentPhaseSection.style.display = 'none'; // Hide comment section after submission
                            if (playerStatementResultsSection) playerStatementResultsSection.style.display = 'none'; // Hide results after comment
                            // Optionally show a "waiting for other players" message
                        }
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
            updatePlayerChoiceStatus(data.players);
            if (data.players[playerId]) {
                playerNameSpan.textContent = data.players[playerId].name;
            }
        } else if (data.player_id === playerId) {
            updatePersonalStats(data.data);
        }
    });

    socket.on('connect', () => {
        console.log('Connected to server');
        // Re-join the game room on reconnection
        if (gameId && playerId) {
            socket.emit('join_game', { game_id: gameId, player_id: playerId });
        }
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
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
            winnerInfo.textContent = `${data.winner.name} has achieved total domination!`;
        } else if (data.reason) {
            winnerInfo.textContent = data.reason;
        } else {
            winnerInfo.textContent = 'The game has ended.';
        }
        gameOverScreen.style.display = 'block';
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

        // Add choice status if available
        if (player.choice !== null) {
            const choiceStatusSpan = document.createElement('span');
            choiceStatusSpan.classList.add('ml-2', 'badge', 'badge-success'); // Bootstrap badge for chosen
            choiceStatusSpan.textContent = 'Chosen';
            playerStatus.appendChild(choiceStatusSpan);
        } else if (player.action_status === 'joined') {
            playerStatus.classList.add('player-joined');
        }
        else if (player.action_status === 'waiting' && player.faction) { // Only show waiting if they are in a faction and waiting for an action
            const choiceStatusSpan = document.createElement('span');
            choiceStatusSpan.classList.add('ml-2', 'badge', 'badge-warning'); // Bootstrap badge for waiting
            choiceStatusSpan.textContent = 'Waiting...';
            playerStatus.appendChild(choiceStatusSpan);
        }

        // Apply glowing effects based on action_status and ready status
        playerStatus.classList.remove('player-name-glow', 'player-dots-glow', 'player-dots-yellow', 'player-name-yellow'); // Remove previous states
        nameSpan.classList.remove('player-name-glow', 'player-name-yellow'); // Remove from nameSpan as well

        if (player.ready) {
            nameSpan.classList.add('player-name-yellow'); // Glowing yellow name for ready players
        } else if (player.action_status === 'waiting') {
            const dotsSpan = document.createElement('span');
            dotsSpan.classList.add('player-dots-glow'); // Original glowing dots for waiting in-game
            dotsSpan.textContent = ' ● ● ●';
            playerStatus.appendChild(dotsSpan);
        } else if (player.action_status === 'done') {
            nameSpan.classList.add('player-name-glow'); // Original glowing name for action done
        }
    }
}

// For the host page (index.html)
const createGameBtn = document.getElementById('createGameBtn');
if (createGameBtn) {
    createGameBtn.addEventListener('click', () => {
        const numPlayers = document.getElementById('numPlayers').value;
        socket.emit('create_game', { num_players: parseInt(numPlayers) });
    });

    socket.on('game_created', (data) => {
        document.getElementById('gameIdDisplay').textContent = data.game_id;
        const playerUrlsDiv = document.getElementById('playerUrls');
        playerUrlsDiv.innerHTML = '';
        for (const playerId in data.player_urls) {
            const url = new URL(data.player_urls[playerId], window.location.origin).href;
            const item = document.createElement('div');
            item.classList.add('list-group-item');

            const qrContainer = document.createElement('div');
            qrContainer.style.float = 'right';
            const qr = qrcode(0, 'L');
            qr.addData(url);
            qr.make();
            qrContainer.innerHTML = qr.createImgTag(4);

            item.innerHTML = `<strong>${data.players[playerId].name}</strong>`;
            item.appendChild(qrContainer);
            playerUrlsDiv.appendChild(item);
        }

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
        document.getElementById('hostControl').style.display = 'block';
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
        if (data.players && data.factions) {
            // This is a faction update, update the player list on the host page
            for (const pid in data.players) {
                updatePlayerStatusOnHost(data.players[pid], pid);
            }
            const factionColumnsDiv = document.getElementById('factionColumns');
            factionColumnsDiv.innerHTML = '';
            for (const factionId in data.factions) {
                const faction = data.factions[factionId];
                const factionCol = document.createElement('div');
                factionCol.classList.add('col-md');
                
                const factionHeader = document.createElement('h5');
                factionHeader.textContent = factionId;
                factionCol.appendChild(factionHeader);
                
                const playerList = document.createElement('ul');
                playerList.classList.add('list-group');
                
                faction.players.forEach(playerId => {
                    const player = data.players[playerId];
                    const playerItem = document.createElement('li');
                    playerItem.classList.add('list-group-item');
                    playerItem.textContent = player.name;
                    playerList.appendChild(playerItem);
                });
                
                factionCol.appendChild(playerList);
                factionColumnsDiv.appendChild(factionCol);
            }
        } else if (data.players) {
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
                statementVoteCountsDiv.innerHTML = '<h6>Statement Vote Distribution:</h6>';
                const statementVoteList = document.createElement('ul');
                statementVoteList.classList.add('list-group');

                // Map player IDs to their names and statements for easier display
                const playerInfo = {};
                for (const pid in data.players) {
                    playerInfo[pid] = {
                        name: data.players[pid].name,
                        statement: data.players[pid].statement || 'No statement submitted'
                    };
                }

                for (const pid in data.statement_vote_counts) {
                    const votes = data.statement_vote_counts[pid];
                    const listItem = document.createElement('li');
                    listItem.classList.add('list-group-item');
                    let statementText = `${playerInfo[pid].name}: "${playerInfo[pid].statement}" - ${votes} votes`;
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

    socket.on('comments_received', (data) => {
        console.log('Comments received:', data);
        const playerCommentsDisplay = document.getElementById('playerCommentsDisplay');
        const commentList = document.getElementById('commentList');
        const hostNarrative = document.getElementById('hostNarrative');
        const statementVotingResultsDisplay = document.getElementById('statementVotingResultsDisplay');

        if (playerCommentsDisplay && commentList && data.comments) {
            statementVotingResultsDisplay.style.display = 'none'; // Hide statement voting results
            playerCommentsDisplay.style.display = 'block'; // Show comments section
            commentList.innerHTML = '<h6>Player Comments:</h6>';

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
            }
            // Hide the player comments display after the narrative is shown
            if (playerCommentsDisplay) playerCommentsDisplay.style.display = 'none';
        }
    });

    socket.on('statements_submitted', (data) => {
        console.log('Statements submitted:', data);
        const hostNarrative = document.getElementById('hostNarrative');
        hostNarrative.innerHTML = '<h5>Player Statements for Voting:</h5>'; // Clear and add a title
        const statementList = document.createElement('ul');
        statementList.classList.add('list-group');
        for (const playerId in data.statements) {
            const statementData = data.statements[playerId];
            const listItem = document.createElement('li');
            listItem.classList.add('list-group-item');
            listItem.textContent = `${statementData.name}: "${statementData.statement}"`;
            statementList.appendChild(listItem);
        }
        hostNarrative.appendChild(statementList);
        hostNarrative.style.display = 'block'; // Ensure hostNarrative is visible
    });
}