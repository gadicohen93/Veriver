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
import { Resource } from "@/lib/types";

type AddResourceDialogProps = {
	isOpen: boolean;
	onOpenChange: (isOpen: boolean) => void;
	newResource: Resource;
	setNewResource: (resource: Resource) => void;
	addResource: () => void;
};

export function AddResourceDialog({
	isOpen,
	onOpenChange,
	newResource,
	setNewResource,
	addResource,
}: AddResourceDialogProps) {
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
						placeholder="Type Telegram Channel Name Here"
						value={newResource.url || ""}
						onChange={(e) =>
							setNewResource({
								...newResource,
								url: e.target.value,
							})
						}
						aria-label="New resource URL"
						className="bg-background"
					/>
				</div>
				<Button
					onClick={addResource}
					className="w-full bg-[#6766FC] text-white"
					disabled={
						!newResource.url ||
						!newResource.title ||
						!newResource.description
					}
				>
					<Plus className="w-4 h-4 mr-2" /> Submit
				</Button>
			</DialogContent>
		</Dialog>
	);
}
