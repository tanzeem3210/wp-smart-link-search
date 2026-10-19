
const API = "";

const uploadForm = document.getElementById("uploadForm");
const searchForm = document.getElementById("searchForm");
const uploadStatus = document.getElementById("uploadStatus");
const searchStatus = document.getElementById("searchStatus");
const results = document.getElementById("results");

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = document.getElementById("chatFile").files[0];
  const groupName = document.getElementById("groupName").value.trim();

  if (!file) {
    uploadStatus.textContent = "Please select a .txt file.";
    return;
  }

  const data = new FormData();
  data.append("file", file);

  if (groupName) {
    data.append("group_name", groupName);
  }

  uploadStatus.textContent = "Uploading and processing chat...";
  const button = uploadForm.querySelector("button");
  button.disabled = true;

  try {
    const response = await fetch(`${API}/api/upload`, {
      method: "POST",
      body: data
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Upload failed.");
    }

    uploadStatus.textContent =
      `Imported "${payload.group_name}": ` +
      `${payload.messages_parsed} messages and ` +
      `${payload.links_found} links found.`;
  } catch (error) {
    uploadStatus.textContent =
      `Error: ${error.message}. Make sure the backend is running.`;
  } finally {
    button.disabled = false;
  }
});

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const keyword = document.getElementById("keyword").value.trim();
  const platform = document.getElementById("platform").value;

  if (!keyword) {
    searchStatus.textContent = "Enter a keyword to search.";
    return;
  }

  searchStatus.textContent = "Searching...";
  results.replaceChildren();

  const params = new URLSearchParams({ q: keyword });
  if (platform) params.set("platform", platform);

  try {
    const response = await fetch(`${API}/api/search?${params}`);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || "Search failed.");
    }

    searchStatus.textContent =
      `${payload.results_count} matching message(s) found.`;

    if (payload.results.length === 0) {
      results.textContent = "No matches found. Try another keyword.";
      return;
    }

    for (const item of payload.results) {
      const card = document.createElement("article");
      card.className = "result";

      const heading = document.createElement("h3");
      heading.textContent = item.group_name || "WhatsApp chat";
      card.appendChild(heading);

      const message = document.createElement("p");
      message.textContent =
        `${item.timestamp || ""} · ${item.sender || "Unknown sender"}: ` +
        item.matched_message;
      card.appendChild(message);

      if (!item.links.length) {
        const note = document.createElement("p");
        note.textContent = "No nearby links for this platform.";
        card.appendChild(note);
      }

      for (const link of item.links) {
        const row = document.createElement("div");
        row.className = "link-item";

        const badge = document.createElement("span");
        badge.className = "platform";
        badge.textContent = link.platform || "Other";
        row.appendChild(badge);

        const url = document.createElement("p");
        const anchor = document.createElement("a");
        anchor.href = link.url;
        anchor.textContent = link.url;
        url.appendChild(anchor);
        row.appendChild(url);

        if (link.link_timestamp) {
          const time = document.createElement("small");
          time.textContent =
            `${link.link_timestamp} · ${link.link_sender || "Unknown sender"}`;
          row.appendChild(time);
        }

        card.appendChild(row);
      }

      results.appendChild(card);
    }
  } catch (error) {
    searchStatus.textContent = `Error: ${error.message}`;
  }
});
