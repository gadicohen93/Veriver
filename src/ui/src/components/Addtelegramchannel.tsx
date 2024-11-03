import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PlusCircle, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

type AddResourceDialogProps = {
	isOpen: boolean;
	onOpenChange: (isOpen: boolean) => void;
};

export function AddResourceDialog({
	isOpen,
	onOpenChange,
}: AddResourceDialogProps) {
	const [channelName, setChannelName] = useState("");
	const [isLoading, setIsLoading] = useState(false);

	const addChannel = async () => {
		try {
			setIsLoading(true);
			const response = await fetch('http://localhost:8000/telegram/subscribe', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					channel: channelName,
				}),
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.detail || 'Failed to add channel');
			}

			toast.success("Channel added successfully!");
			setChannelName("");
			onOpenChange(false);
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Failed to add channel');
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<Dialog open={isOpen} onOpenChange={onOpenChange}>
			<DialogTrigger asChild>
				<Button
					variant="link"
					size="sm"
					className="text-sm font-bold text-[#6766FC]"
				>
					Add Telegram Channel <PlusCircle className="w-6 h-6 ml-2" />
				</Button>
			</DialogTrigger>
			<DialogContent className="sm:max-w-[425px]">
				<DialogHeader>
					<DialogTitle>Adding a Telegram Channel</DialogTitle>
				</DialogHeader>
				<div className="grid gap-4 py-4">
					<label htmlFor="new-url" className="text-sm font-bold">
						Telegram Channel
					</label>
					<Input
						id="new-url"
						placeholder="Enter channel username (e.g. @channelname) or URL"
						value={channelName}
						onChange={(e) => setChannelName(e.target.value)}
						aria-label="New channel name"
						className="bg-background"
					/>
				</div>
				<Button
					onClick={addChannel}
					className="w-full bg-[#6766FC] text-white"
					disabled={!channelName || isLoading}
				>
					{isLoading ? (
						<>Loading...</>
					) : (
						<>
							<Plus className="w-4 h-4 mr-2" /> Submit
						</>
					)}
				</Button>
			</DialogContent>
		</Dialog>
	);
}
