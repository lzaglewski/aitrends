// API Client for AI Trends Monitor
const API_BASE_URL = 'http://localhost:8000';

class APIClient {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    // Helper method for making requests
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;

        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                },
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    // Sources endpoints
    async getSources(activeOnly = true) {
        return this.request(`/sources?active_only=${activeOnly}`);
    }

    async addSource(name, url, sourceType) {
        return this.request('/sources', {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                url: url,
                source_type: sourceType
            })
        });
    }

    async updateSource(sourceId, name, url, sourceType) {
        return this.request(`/sources/${sourceId}`, {
            method: 'PUT',
            body: JSON.stringify({
                name: name,
                url: url,
                source_type: sourceType
            })
        });
    }

    async deleteSource(sourceId) {
        return this.request(`/sources/${sourceId}`, {
            method: 'DELETE'
        });
    }

    // Articles endpoints
    async getArticles(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.keyword) queryParams.append('keyword', params.keyword);
        if (params.source_id) queryParams.append('source_id', params.source_id);
        if (params.days) queryParams.append('days', params.days);
        if (params.limit) queryParams.append('limit', params.limit);

        const query = queryParams.toString();
        return this.request(`/articles${query ? '?' + query : ''}`);
    }

    // Trends endpoints
    async getTrends(days = 30, limit = 20) {
        return this.request(`/trends?days=${days}&limit=${limit}`);
    }

    async getEmergingTrends(days = 30, limit = 20) {
        return this.request(`/trends/emerging?days=${days}&limit=${limit}`);
    }

    async getDecliningTrends(days = 30, limit = 20) {
        return this.request(`/trends/declining?days=${days}&limit=${limit}`);
    }

    async getTrendsSummary(days = 30) {
        return this.request(`/trends/summary?days=${days}`);
    }

    // Keywords endpoints
    async getKeywords(limit = 50) {
        return this.request(`/keywords?limit=${limit}`);
    }

    // Stats endpoints
    async getStats() {
        return this.request('/stats');
    }

    async getHealth() {
        return this.request('/health');
    }

    // Scraping endpoints
    async triggerScraping() {
        return this.request('/scrape/trigger', {
            method: 'POST'
        });
    }
}

// Create a global instance
const api = new APIClient();
