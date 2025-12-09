/**
 * Frontend JavaScript for Semantic Earnings Reversal Framework
 *
 * Handles:
 * - Form submission and API calls
 * - Rendering analysis results
 * - Interactive UI elements
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('analyze-form');
    const tickerInput = document.getElementById('ticker');
    const analyzeBtn = document.getElementById('analyze-btn');
    const loadingDiv = document.getElementById('loading');
    const loadingText = document.getElementById('loading-text');
    const errorDiv = document.getElementById('error');
    const errorMessage = document.getElementById('error-message');
    const resultsDiv = document.getElementById('results');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const ticker = tickerInput.value.trim().toUpperCase();
        if (!ticker) {
            showError('Please enter a valid ticker symbol');
            return;
        }

        // Reset UI state
        hideAll();
        showLoading();
        analyzeBtn.disabled = true;

        try {
            const response = await fetch(`/api/analyze?ticker=${encodeURIComponent(ticker)}`);

            if (!response.ok) {
                const errorData = await response.json();
                // Handle structured error response
                const errorMsg = errorData.detail?.message || errorData.detail || `HTTP error ${response.status}`;
                throw new Error(errorMsg);
            }

            const data = await response.json();
            renderResults(data);

        } catch (error) {
            console.error('Analysis error:', error);
            showError(error.message || 'An unexpected error occurred');
        } finally {
            analyzeBtn.disabled = false;
            loadingDiv.classList.add('hidden');
        }
    });

    function hideAll() {
        loadingDiv.classList.add('hidden');
        errorDiv.classList.add('hidden');
        resultsDiv.classList.add('hidden');
    }

    function showLoading() {
        loadingDiv.classList.remove('hidden');
        loadingText.textContent = 'Fetching earnings data and transcripts...';

        // Update loading message periodically
        let step = 0;
        const messages = [
            'Fetching earnings data and transcripts...',
            'Analyzing transcripts with AI...',
            'Calculating semantic signals...',
            'Computing forward returns...'
        ];

        const interval = setInterval(() => {
            step = (step + 1) % messages.length;
            loadingText.textContent = messages[step];

            if (loadingDiv.classList.contains('hidden')) {
                clearInterval(interval);
            }
        }, 5000);
    }

    function showError(message) {
        hideAll();
        errorMessage.textContent = message;
        errorDiv.classList.remove('hidden');
    }

    function renderResults(data) {
        hideAll();

        // Set ticker in header
        document.getElementById('result-ticker').textContent = data.ticker;

        // Set analysis status stats
        document.getElementById('stat-events-found').textContent = data.total_events_found || 0;
        document.getElementById('stat-events-analyzed').textContent = data.events_analyzed || 0;
        document.getElementById('stat-events-signals').textContent = data.events_with_signals || 0;

        // Render hit rate cards
        renderHitRateCards(data.summary.hit_rates);

        // Render events table
        renderEventsTable(data.events);

        resultsDiv.classList.remove('hidden');
    }

    function renderHitRateCards(hitRates) {
        const container = document.getElementById('hit-rate-cards');
        container.innerHTML = '';

        const horizons = ['5', '10', '30', '60'];

        horizons.forEach(h => {
            const stats = hitRates[h] || { num_trades: 0, num_hits: 0, hit_rate: null };
            const hitRateText = stats.hit_rate !== null
                ? `${(stats.hit_rate * 100).toFixed(1)}%`
                : 'N/A';

            const hitRateColor = stats.hit_rate !== null
                ? (stats.hit_rate >= 0.5 ? 'text-green-600' : 'text-red-600')
                : 'text-gray-400';

            const card = document.createElement('div');
            card.className = 'bg-gray-50 rounded-lg p-4 text-center';
            card.innerHTML = `
                <div class="text-sm text-gray-500 mb-1">T+${h} Days</div>
                <div class="text-2xl font-bold ${hitRateColor}">${hitRateText}</div>
                <div class="text-xs text-gray-400 mt-1">${stats.num_hits}/${stats.num_trades} trades</div>
            `;
            container.appendChild(card);
        });
    }

    function renderEventsTable(events) {
        const tbody = document.getElementById('events-body');
        tbody.innerHTML = '';

        events.forEach((event, index) => {
            // Main row
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50 cursor-pointer expand-btn';
            row.dataset.index = index;

            row.innerHTML = `
                <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    ${event.earning_date}
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    ${formatEPS(event.eps, event.eps_estimate)}
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-sm ${event.day0_return >= 0 ? 'text-green-600' : 'text-red-600'}">
                    ${formatPercent(event.day0_return)}
                </td>
                ${renderSignalCell(event.signals.tone_numbers)}
                ${renderSignalCell(event.signals.prepared_vs_qa)}
                ${renderSignalCell(event.signals.regime_shift)}
                ${renderSignalCell(event.signals.temp_vs_struct)}
                ${renderSignalCell(event.signals.analyst_skepticism)}
                ${renderSignalCell(event.signals.final_signal, true)}
                ${renderForwardReturnCells(event.forward_returns)}
            `;

            row.addEventListener('click', () => toggleDetails(index));
            tbody.appendChild(row);

            // Detail row (hidden by default)
            const detailRow = document.createElement('tr');
            detailRow.className = 'event-details bg-gray-50';
            detailRow.id = `details-${index}`;
            detailRow.innerHTML = `
                <td colspan="13" class="px-4 py-4">
                    ${renderEventDetails(event)}
                </td>
            `;
            tbody.appendChild(detailRow);
        });
    }

    function formatEPS(actual, estimate) {
        const actualStr = actual !== null ? actual.toFixed(2) : 'N/A';
        const estimateStr = estimate !== null ? estimate.toFixed(2) : 'N/A';
        const surprise = (actual !== null && estimate !== null)
            ? ((actual - estimate) / Math.abs(estimate) * 100).toFixed(1)
            : null;

        let surpriseHtml = '';
        if (surprise !== null) {
            const color = parseFloat(surprise) >= 0 ? 'text-green-600' : 'text-red-600';
            surpriseHtml = `<span class="${color}">(${surprise > 0 ? '+' : ''}${surprise}%)</span>`;
        }

        return `${actualStr} / ${estimateStr} ${surpriseHtml}`;
    }

    function formatPercent(value) {
        if (value === null || value === undefined) return 'N/A';
        const sign = value >= 0 ? '+' : '';
        return `${sign}${(value * 100).toFixed(1)}%`;
    }

    function renderSignalCell(signal, isFinal = false) {
        const bgClass = isFinal ? 'bg-blue-50' : '';
        let scoreClass = 'signal-neutral';
        let scoreText = signal.score.toFixed(1);

        // 0-10 scale: > 5.5 = bullish, < 4.5 = bearish, 4.5-5.5 = neutral
        if (signal.score > 5.5) {
            scoreClass = 'signal-positive';
        } else if (signal.score < 4.5) {
            scoreClass = 'signal-negative';
        }

        return `
            <td class="px-4 py-3 text-center ${bgClass}">
                <span class="tooltip ${scoreClass}">
                    ${scoreText}
                    <span class="tooltip-text">${signal.explanation}</span>
                </span>
            </td>
        `;
    }

    function renderForwardReturnCells(forwardReturns) {
        const horizons = [5, 10, 30, 60];
        let html = '';

        horizons.forEach(h => {
            const fr = forwardReturns.find(r => r.horizon === h);

            if (!fr) {
                html += `<td class="px-4 py-3 text-center text-gray-400 text-sm">-</td>`;
                return;
            }

            const returnColor = fr.return_pct >= 0 ? 'text-green-600' : 'text-red-600';
            let hitIcon = '';
            let hitClass = '';

            if (fr.hit === true) {
                hitIcon = ' ✓';
                hitClass = 'hit-true';
            } else if (fr.hit === false) {
                hitIcon = ' ✗';
                hitClass = 'hit-false';
            } else {
                hitIcon = '';
                hitClass = 'hit-na';
            }

            html += `
                <td class="px-4 py-3 text-center text-sm">
                    <span class="${returnColor}">${formatPercent(fr.return_pct)}</span>
                    <span class="${hitClass}">${hitIcon}</span>
                </td>
            `;
        });

        return html;
    }

    function renderEventDetails(event) {
        const features = event.semantic_features;

        return `
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                <!-- Summary -->
                <div class="col-span-full bg-white p-3 rounded border">
                    <div class="font-medium text-gray-700 mb-1">AI Summary</div>
                    <div class="text-gray-600">${features.one_sentence_summary}</div>
                </div>

                <!-- Numbers View -->
                <div class="bg-white p-3 rounded border">
                    <div class="font-medium text-gray-700 mb-2">Numbers Assessment</div>
                    <div class="space-y-1 text-gray-600">
                        <div>EPS Strength: ${renderStrength(features.numbers.eps_strength)}</div>
                        <div>Revenue Strength: ${renderStrength(features.numbers.revenue_strength)}</div>
                        <div>Overall: ${renderStrength(features.numbers.overall_numbers_strength)}</div>
                    </div>
                </div>

                <!-- Tone View -->
                <div class="bg-white p-3 rounded border">
                    <div class="font-medium text-gray-700 mb-2">Tone Analysis</div>
                    <div class="space-y-1 text-gray-600">
                        <div>Overall Tone: ${renderStrength(features.tone.overall_tone)}</div>
                        <div>Prepared Remarks: ${renderStrength(features.tone.prepared_tone)}</div>
                        <div>Q&A Session: ${renderStrength(features.tone.qa_tone)}</div>
                    </div>
                </div>

                <!-- Risk Focus -->
                <div class="bg-white p-3 rounded border">
                    <div class="font-medium text-gray-700 mb-2">Risk Focus</div>
                    <div class="space-y-1 text-gray-600">
                        <div>Risk Score: ${features.risk_focus_score}/100</div>
                        <div class="w-full bg-gray-200 rounded-full h-2.5">
                            <div class="bg-orange-500 h-2.5 rounded-full" style="width: ${features.risk_focus_score}%"></div>
                        </div>
                    </div>
                </div>

                <!-- Narrative View -->
                <div class="bg-white p-3 rounded border">
                    <div class="font-medium text-gray-700 mb-2">Narrative Analysis</div>
                    <div class="space-y-1 text-gray-600">
                        <div>Neg Temporary: ${(features.narrative.neg_temporary_ratio * 100).toFixed(0)}%</div>
                        <div>Pos Temporary: ${(features.narrative.pos_temporary_ratio * 100).toFixed(0)}%</div>
                    </div>
                </div>

                <!-- Skepticism View -->
                <div class="bg-white p-3 rounded border">
                    <div class="font-medium text-gray-700 mb-2">Analyst Behavior</div>
                    <div class="space-y-1 text-gray-600">
                        <div>Skeptical Questions: ${(features.skepticism.skeptical_question_ratio * 100).toFixed(0)}%</div>
                        <div>Follow-ups: ${(features.skepticism.followup_ratio * 100).toFixed(0)}%</div>
                        <div>Topic Concentration: ${(features.skepticism.topic_concentration * 100).toFixed(0)}%</div>
                    </div>
                </div>

                <!-- Signal Details -->
                <div class="bg-white p-3 rounded border col-span-full">
                    <div class="font-medium text-gray-700 mb-2">Signal Explanations</div>
                    <div class="space-y-2 text-gray-600">
                        <div><strong>Tone-Numbers:</strong> ${event.signals.tone_numbers.explanation}</div>
                        <div><strong>Prepared vs Q&A:</strong> ${event.signals.prepared_vs_qa.explanation}</div>
                        <div><strong>Regime Shift:</strong> ${event.signals.regime_shift.explanation}</div>
                        <div><strong>Temp vs Struct:</strong> ${event.signals.temp_vs_struct.explanation}</div>
                        <div><strong>Analyst Skepticism:</strong> ${event.signals.analyst_skepticism.explanation}</div>
                        <div class="font-medium text-blue-700"><strong>Final Signal:</strong> ${event.signals.final_signal.explanation}</div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderStrength(value) {
        const labels = {
            '-2': '<span class="text-red-600 font-medium">Very Negative (-2)</span>',
            '-1': '<span class="text-red-500">Negative (-1)</span>',
            '0': '<span class="text-gray-500">Neutral (0)</span>',
            '1': '<span class="text-green-500">Positive (+1)</span>',
            '2': '<span class="text-green-600 font-medium">Very Positive (+2)</span>'
        };
        return labels[value.toString()] || `${value}`;
    }

    function toggleDetails(index) {
        const detailRow = document.getElementById(`details-${index}`);
        if (detailRow) {
            detailRow.classList.toggle('expanded');
        }
    }
});
