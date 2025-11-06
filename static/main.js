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
    // const dilemmaChoices = document.getElementById('dilemmaChoices'); // Moved to local scope
const playerStatementInput = document.getElementById('playerStatementInput');
const submitStatementBtn = document.getElementById('submitStatementBtn');

const narrativeOutput = document.getElementById('narrativeOutput');
const narrativeText = document.getElementById('narrativeText');
const nextRoundBtn = document.getElementById('nextRoundBtn');

let playerChoice = null;

function updatePersonalStats(playerData) {
    if (playerData && playerData.personal_stats) {
        const influence = playerData.personal_stats.Influence;
        statInfluenceSpan.style.width = `${influence}%`;
        statInfluenceSpan.setAttribute('aria-valuenow', influence);
        statInfluenceSpan.textContent = `${influence}`; // Display number inside bar
    }
}

function renderDilemma(dilemma) {
    dilemmaTitle.textContent = dilemma.title;
    dilemmaDescription.textContent = dilemma.description;
    if (dilemma.image) {
        dilemmaImage.src = dilemma.image;
        dilemmaImage.style.display = 'block';
    } else {
        dilemmaImage.style.display = 'none';
    }

    dilemmaChoices.innerHTML = '';
    dilemma.choices.forEach((choice, index) => {
        const button = document.createElement('button');
        button.classList.add('list-group-item', 'list-group-item-action', 'mb-2');
        button.textContent = choice.text;
        button.addEventListener('click', () => {
            playerChoice = index;
            socket.emit('player_action', { game_id: gameId, player_id: playerId, action: 'dilemma_choice', choice: index });
            // Disable choices after selection
            Array.from(dilemmaChoices.children).forEach(btn => btn.disabled = true);
            button.classList.add('active');

            // Hide dilemma and show statement section
            document.getElementById('dilemmaSection').style.display = 'none';
            document.getElementById('playerStatementsSection').style.display = 'block';
        });
        dilemmaChoices.appendChild(button);
    });
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
    const hostGameArea = document.getElementById('hostGameArea');
    const debugMessage = document.getElementById('debugMessage');

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

                // document.getElementById('votingStatus').style.display = 'block'; // Removed votingStatus

                

                // Hide all lobby-specific elements

                document.getElementById('gameControlHeader').style.display = 'none';

                document.getElementById('gameIdContainer').style.display = 'none';

                document.getElementById('playerLinksHeader').style.display = 'none';

                document.getElementById('playerUrls').style.display = 'none';

                document.getElementById('playerStatusHeader').style.display = 'none';

                document.getElementById('playerStatus').style.display = 'none';

    

        } else if (gameArea) {

            // Player

            waitingRoom.style.display = 'none';

            gameArea.style.display = 'block';

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
                const dilemmaChoices = document.getElementById('dilemmaChoices'); // Select element just-in-time
                if (!dilemmaChoices) {
                    console.error('Could not find dilemmaChoices element!');
                    return; 
                }

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
                        playerChoice = index;
                        socket.emit('player_action', { game_id: gameId, player_id: playerId, action: 'dilemma_choice', choice: index });
                        // Disable choices after selection
                        Array.from(dilemmaChoices.children).forEach(btn => btn.disabled = true);
                        button.classList.add('active');

                        // Hide dilemma and show statement section
                        document.getElementById('dilemmaSection').style.display = 'none';
                        document.getElementById('playerStatementsSection').style.display = 'block';
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
                const dilemmaSection = document.getElementById('dilemmaSection');
                if (dilemmaSection) {
                    dilemmaSection.style.display = 'block';
                }
                const playerStatementsSection = document.getElementById('playerStatementsSection');
                if (playerStatementsSection) {
                    playerStatementsSection.style.display = 'none';
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
        narrativeText.textContent = data.outcome; // Set text content
        narrativeText.style.display = 'none'; // Explicitly hide the narrative text
        currentRoundSpan.textContent = data.current_round;
        narrativeOutput.style.display = 'block'; // Show narrativeOutput to display the button
        document.getElementById('nextRoundBtn').style.display = 'block'; // Show the Next Event button
        dilemmaSection.style.display = 'none';
        playerStatementsSection.style.display = 'none';
        waitingRoom.style.display = 'none';
    });

    socket.on('phase_change', (data) => {
        if (data.phase === 'STATEMENT_VOTE') {
            document.getElementById('playerStatementsSection').style.display = 'none'; // Hide statement submission
            const statementVoteSection = document.getElementById('statementVoteSection');
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
                                        statementVoteSection.style.display = 'none';
                                    });                listItem.appendChild(voteButton);
                statementVoteList.appendChild(listItem);
            }
            statementVoteSection.style.display = 'block'; // Show voting section
        }
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
}
function updatePlayerStatusOnHost(player, playerId) {
    const playerStatus = document.getElementById(`player-status-${playerId}`);
    if (playerStatus) {
        let statusText = player.name;
        if (player.faction) {
            statusText += ` (${player.faction})`;
        }
        if (player.ready) {
            statusText += ' (Ready)';
        }

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
        } else if (player.action_status === 'waiting' && player.faction) { // Only show waiting if they are in a faction and waiting for an action
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
        } else if (player.action_status === 'joined') {
            const dotsSpan = document.createElement('span');
            dotsSpan.classList.add('player-dots-yellow'); // Yellow glowing dots for joined but not ready
            dotsSpan.textContent = ' ● ● ●';
            playerStatus.appendChild(dotsSpan);
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
        document.getElementById('hostNarrative').textContent = data.outcome;
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
        document.getElementById('votingStatus').style.display = 'none'; // Hide voting status
        document.getElementById('playerStatements').style.display = 'none'; // Hide the original playerStatements div
        hostNarrative.style.display = 'block'; // Ensure hostNarrative is visible
    });
}