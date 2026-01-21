/**
 * Vedic Numerology-Astrology API Client
 * =====================================
 *
 * JavaScript client for interacting with the Vedic Numerology API
 * Supports multiple deployment methods: FastAPI server, GitHub Actions, Streamlit
 */

class VedicNumerologyAPI {
    constructor(options = {}) {
        this.baseURL = options.baseURL || this.detectEnvironment();
        this.timeout = options.timeout || 30000; // 30 seconds
        this.retryAttempts = options.retryAttempts || 3;
    }

    /**
     * Auto-detect API environment based on current location
     */
    detectEnvironment() {
        const hostname = window.location.hostname;

        // Local development
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://localhost:8000';
        }

        // GitHub Pages (use GitHub Actions webhook API)
        if (hostname.includes('github.io')) {
            return 'https://api.github.com/repos/astro-fusion/numerology-white-paper/dispatches';
        }

        // Default to deployed API
        return 'https://vedic-numerology-api.onrender.com';
    }

    /**
     * Make HTTP request with retry logic
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        // Add body for POST requests
        if (options.body && typeof options.body === 'object') {
            config.body = JSON.stringify(options.body);
        }

        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                const response = await fetch(url, config);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                return await response.json();
            } catch (error) {
                console.warn(`API request attempt ${attempt} failed:`, error.message);

                if (attempt === this.retryAttempts) {
                    throw new Error(`API request failed after ${this.retryAttempts} attempts: ${error.message}`);
                }

                // Wait before retry (exponential backoff)
                await this.delay(Math.pow(2, attempt) * 1000);
            }
        }
    }

    /**
     * Utility delay function
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Calculate numerology for birth data
     */
    async calculateNumerology(birthData) {
        const payload = {
            birth_date: birthData.birth_date,
            birth_time: birthData.birth_time || '12:00',
            latitude: birthData.latitude || 28.6139,
            longitude: birthData.longitude || 77.1025,
            timezone: birthData.timezone || 'Asia/Kolkata',
            ayanamsa_system: birthData.ayanamsa_system || 'lahiri'
        };

        // Use direct API for deployed services
        // Note: GitHub Actions webhook requires backend authentication and is not suitable for browser clients
        return this.request('/api/v1/numerology', {
            method: 'POST',
            body: payload
        });
    }

    /**
     * Calculate astrology for birth data
     */
    async calculateAstrology(birthData) {
        const payload = {
            birth_date: birthData.birth_date,
            birth_time: birthData.birth_time || '12:00',
            latitude: birthData.latitude || 28.6139,
            longitude: birthData.longitude || 77.1025,
            timezone: birthData.timezone || 'Asia/Kolkata',
            ayanamsa_system: birthData.ayanamsa_system || 'lahiri'
        };

        // Use direct API for deployed services
        // Note: GitHub Actions webhook requires backend authentication and is not suitable for browser clients
        return this.request('/api/v1/astrology', {
            method: 'POST',
            body: payload
        });
    }

    /**
     * Perform complete analysis (numerology + astrology)
     */
    async completeAnalysis(birthData) {
        const payload = {
            birth_date: birthData.birth_date,
            birth_time: birthData.birth_time || '12:00',
            latitude: birthData.latitude || 28.6139,
            longitude: birthData.longitude || 77.1025,
            timezone: birthData.timezone || 'Asia/Kolkata',
            ayanamsa_system: birthData.ayanamsa_system || 'lahiri'
        };

        // Use direct API for deployed services
        // Note: GitHub Actions webhook requires backend authentication and is not suitable for browser clients
        return this.request('/api/v1/analysis', {
            method: 'POST',
            body: payload
        });
    }

    /**
     * Call GitHub Actions via repository dispatch
     * Note: Requires GitHub token with repo scope
     */
    async callGitHubActions(eventType, payload, githubToken = null) {
        // For GitHub Actions webhook, we need to trigger a repository dispatch
        // This will run the GitHub Actions workflow and return results

        if (!githubToken) {
            throw new Error('GitHub token required for Actions API. This should be called from a backend service.');
        }

        const webhookPayload = {
            event_type: eventType,
            client_payload: {
                ...payload,
                // Add issue number if available (for commenting on issues)
                issue_number: null
            }
        };

        try {
            const response = await this.request('', {
                method: 'POST',
                headers: {
                    'Authorization': `token ${githubToken}`,
                    'Accept': 'application/vnd.github.v3+json'
                },
                body: webhookPayload
            });

            // GitHub Actions will process this asynchronously
            // For immediate response, we'd need to poll or use webhooks
            return {
                status: 'processing',
                message: 'Calculation started via GitHub Actions',
                workflow_url: `https://github.com/astro-fusion/numerology-white-paper/actions`,
                payload: webhookPayload
            };

        } catch (error) {
            // Fallback: Show how to trigger manually
            return {
                status: 'manual_required',
                message: 'Please trigger calculation manually via GitHub Actions',
                manual_url: `https://github.com/astro-fusion/numerology-white-paper/actions/workflows/api-webhook.yml`,
                payload: payload
            };
        }
    }

    /**
     * Get API health status
     */
    async healthCheck() {
        try {
            return await this.request('/api/v1/health');
        } catch (error) {
            return { status: 'unavailable', error: error.message };
        }
    }

    /**
     * Get planets information
     */
    async getPlanets() {
        return this.request('/api/v1/planets');
    }

    /**
     * Get API examples and documentation
     */
    async getExamples() {
        return this.request('/api/v1/examples');
    }

    /**
     * Get astrology dignity strength time-series.
     */
    async getPlanetStrengthSeries(params) {
        const qs = new URLSearchParams({
            start: params.start,
            end: params.end,
            step_days: String(params.step_days || 1),
        });
        if (params.planets) qs.set('planets', params.planets); // e.g. "MARS,VENUS"
        if (params.latitude != null) qs.set('latitude', String(params.latitude));
        if (params.longitude != null) qs.set('longitude', String(params.longitude));
        return this.request(`/api/v1/planet-strength-series?${qs.toString()}`);
    }

    /**
     * Get numerology (Mulanka active planet) time-series.
     */
    async getNumerologySeries(params) {
        const qs = new URLSearchParams({
            start: params.start,
            end: params.end,
            step_days: String(params.step_days || 1),
        });
        if (params.planets) qs.set('planets', params.planets);
        return this.request(`/api/v1/numerology-series?${qs.toString()}`);
    }

    /**
     * Get combined numerology + astrology time-series.
     */
    async getCombinedSeries(params) {
        const qs = new URLSearchParams({
            start: params.start,
            end: params.end,
            step_days: String(params.step_days || 1),
        });
        if (params.planets) qs.set('planets', params.planets);
        if (params.latitude != null) qs.set('latitude', String(params.latitude));
        if (params.longitude != null) qs.set('longitude', String(params.longitude));
        return this.request(`/api/v1/combined-series?${qs.toString()}`);
    }
}

// Global API instance
const vedicAPI = new VedicNumerologyAPI();

// Utility functions for UI integration
function formatNumerologyResult(result) {
    return {
        mulanka: {
            number: result.mulanka.number,
            planet: result.mulanka.planet,
            display: `${result.mulanka.number} (${result.mulanka.planet})`
        },
        bhagyanka: {
            number: result.bhagyanka.number,
            planet: result.bhagyanka.planet,
            display: `${result.bhagyanka.number} (${result.bhagyanka.planet})`
        },
        timestamp: result.timestamp
    };
}

function formatSupportAnalysis(analysis) {
    return {
        mulanka: {
            support: analysis.mulanka.support_level,
            score: analysis.mulanka.score,
            planet: analysis.mulanka.planet
        },
        bhagyanka: {
            support: analysis.bhagyanka.support_level,
            score: analysis.bhagyanka.score,
            planet: analysis.bhagyanka.planet
        },
        overall: {
            harmony: analysis.overall.harmony_level,
            averageScore: analysis.overall.average_score
        }
    };
}

// Export for different environments
if (typeof module !== 'undefined' && module.exports) {
    // Node.js/CommonJS
    module.exports = { VedicNumerologyAPI, vedicAPI };
} else if (typeof define === 'function' && define.amd) {
    // AMD
    define([], function() {
        return { VedicNumerologyAPI, vedicAPI };
    });
} else {
    // Browser global
    window.VedicNumerologyAPI = VedicNumerologyAPI;
    window.vedicAPI = vedicAPI;
}