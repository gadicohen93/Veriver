export async function fetchTelegramMessages(hours: number = 1) {
  const response = await fetch(`http://localhost:8000/telegram/messages?hours=${hours}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch messages: ${response.statusText}, ${response.status}, ${response.body}`);
  }
  return response.json();
}

export async function fetchLatestTelegramMessages(limit: number = 10) {
  const response = await fetch(`http://localhost:8000/telegram/latest-messages?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch messages: ${response.statusText}, ${response.status}, ${response.body}`);
  }
  return response.json();
}